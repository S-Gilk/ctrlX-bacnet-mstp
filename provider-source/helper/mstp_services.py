#!/usr/bin/env python3
# BACpypes 0.18.x + Misty MSTP
import configparser, json, re, threading, time
from queue import Queue, Empty
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import os, json


from bacpypes.core import run, stop, deferred, enable_sleeping
from bacpypes.pdu import Address, GlobalBroadcast
from bacpypes.apdu import (
    WhoIsRequest, IAmRequest,
    ReadPropertyRequest, ReadPropertyACK,
    WritePropertyRequest, SimpleAckPDU,
)
from bacpypes.local.device import LocalDeviceObject
from bacpypes.object import get_datatype
from bacpypes.constructeddata import Array, Any as AnyCD, AnyAtomic
from bacpypes.primitivedata import (
    Null, Atomic, Boolean, Integer, Real, Double, Unsigned, OctetString,
    CharacterString, BitString, Date, Time, ObjectIdentifier,
)
from bacpypes.iocb import IOCB
from misty.mstplib import MSTPSimpleApplication

from defines import ACTIVE_BACNET_DEFINES_PATH

# ---------------------------
# Normalization helpers
# ---------------------------

_TRUE_WORDS  = {"1", "true", "on", "active", "enabled", "enable", "set"}
_FALSE_WORDS = {"0", "false", "off", "inactive", "disabled", "disable", "reset", "clear"}

def _to_boolish(value: Any) -> bool:
    """
    Best-effort conversion of 'active'/'inactive', on/off, 1/0, True/False, etc. to Python bool.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value).strip().lower()
    if s in _TRUE_WORDS:
        return True
    if s in _FALSE_WORDS:
        return False
    # Fallback: anything non-empty/non-zero-ish → True
    try:
        return bool(int(s))
    except Exception:
        return len(s) > 0
    
def _to_int(value: Any) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    return int(round(float(value))) if isinstance(value, (int, float)) else int(str(value).strip())


def _to_float(value: Any) -> float:
    return float(value)


def _to_str(value: Any) -> str:
    return "" if value is None else str(value)

# - BACNET Object Type Defintiions

# In-memory store
_OBJECT_TYPE_DEFS: dict[str, dict] = {}

def load_object_type_definitions(json_path: str | Path | None = None) -> None:
    """
    Load object-type definitions from JSON (required). Normalizes values.
    Schema per object_type:
      {"access": "R"|"R/W", "bacnet_type": "<ENUM>", "datalayer_type": "<ENUM>"}
    """
    path = Path(json_path or ACTIVE_BACNET_DEFINES_PATH)
    if not path.exists():
        raise FileNotFoundError(f"BACnet type definitions JSON not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("type_defs JSON root must be an object")

    norm: dict[str, dict] = {}
    for k, v in data.items():
        if not isinstance(v, dict):
            continue

        obj_type = str(k)
        access = str(v.get("access", "R")).upper().strip()
        bacnet_type = str(v.get("bacnet_type", "UNKNOWN")).upper().strip()
        dl_type = str(v.get("datalayer_type", "STRING")).upper().strip()
        uninit_default = v.get("uninitialized_default", None)

        if access not in {"R", "R/W"}:
            raise ValueError(f"Invalid access for {obj_type}: {access}")

        # Normalize JSON 'null' to None
        if isinstance(uninit_default, str) and uninit_default.lower() in ("none", "null"):
            uninit_default = None

        norm[obj_type] = {
            "access": access,
            "bacnet_type": bacnet_type,
            "datalayer_type": dl_type,
            "uninitialized_default": uninit_default,
        }

    _OBJECT_TYPE_DEFS.clear()
    _OBJECT_TYPE_DEFS.update(norm)

def get_object_def(obj_type: str) -> dict | None:
    """Return full definition dict for an object type, or None if unknown."""
    return _OBJECT_TYPE_DEFS.get(obj_type)

def get_uninitialized_default(obj_type: str):
    d = _OBJECT_TYPE_DEFS.get(obj_type)
    return d.get("uninitialized_default") if d else None

def get_bacnet_type(obj_type: str) -> str | None:
    d = get_object_def(obj_type)
    return d["bacnet_type"] if d else None

def get_datalayer_type(obj_type: str) -> str | None:
    d = get_object_def(obj_type)
    return d["datalayer_type"] if d else None

def get_access(obj_type: str) -> str | None:
    d = get_object_def(obj_type)
    return d["access"] if d else None

# ---- Simple in-memory Device Cache ----
from threading import RLock

device_cache: dict[int, dict] = {}
device_cache_lock = RLock()


def clear_device_cache():
    """Clear all cached Who-Is results."""
    with device_cache_lock:
        device_cache.clear()


def cache_device(device: dict):
    """Store or update a device entry from whois() results."""
    device_id = device.get("device_instance")
    if device_id is None:
        return
    with device_cache_lock:
        device_cache[device_id] = device


def get_device_by_id(device_id: int) -> dict | None:
    """Return the cached device info dict for a device_instance."""
    with device_cache_lock:
        return device_cache.get(device_id)


def get_mac_for_device(device_id: int) -> int | None:
    """Return cached MAC for a device_instance (if known)."""
    with device_cache_lock:
        dev = device_cache.get(device_id)
        if not dev:
            return None
        return dev.get("source_mac")

def _json_safe(seq):
    out = []
    for v in seq:
        try:
            json.dumps(v)
            out.append(v)
        except TypeError:
            out.append(str(v))
    return out


# ------------------------- INI / SETUP -------------------------

# ------------------------- PUBLIC INIT/HELPERS (no Who-Is) -------------------------

def mstp_init_only(
    ini_path: str = "bc.ini",
    *,
    start_core: bool = True,
    wait_online_timeout: float = 0.0,
) -> dict:
    """
    Initialize from bc.ini WITHOUT sending any traffic (no Who-Is).
    Optionally start the BACpypes core and wait for the MS/TP port to come online.

    Returns a small status dict; use get_app()/get_port() for objects if needed.
    """
    _Core.ensure_started(ini_path)
    started = True

    core_thread = None
    if start_core:
        # If ensure_started() already created the core thread, this is a no-op.
        # Otherwise it will start it now.
        # (ensure_started already starts the core thread; we just mirror intent.)
        started = True

    online = False
    if wait_online_timeout > 0.0:
        port = get_port()
        if port is not None:
            online = _wait_until_online(port, timeout=wait_online_timeout)
        else:
            # No visible port attribute; fall back to a simple sleep so the token
            # acquisition can complete before the caller does anything.
            import time as _time
            _time.sleep(wait_online_timeout)

    return {"initialized": True, "core_started": started, "online": online}


def get_app():
    """
    Access the live MSTP application (after init_only/ensure_started).
    """
    return _Core.app()


def get_local_device():
    """
    Convenience accessor for the LocalDeviceObject.
    """
    return _Core.app().localDevice


def get_port():
    """
    Best-effort accessor for the underlying MS/TP port/node.
    """
    app = _Core.app()
    # Common names we've seen for MS/TP port attributes
    for attr in ("mstp_port", "mstp", "port"):
        if hasattr(app, attr):
            return getattr(app, attr)
    return None


def mstp_shutdown():
    """
    Cleanly stop the BACpypes core. Safe to call multiple times.
    """
    try:
        stop()
    except Exception:
        pass

def load_bc_ini(path: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    print("LOADING INI")
    # accept ":" and "=" as delimiters (your sample uses ":")
    cp = configparser.ConfigParser(
        delimiters=("=", ":"),
        interpolation=None
    )
    # read the file normally; this auto-handles encoding and newlines
    read_ok = cp.read(path)
    if not read_ok:
        raise FileNotFoundError(f"Could not read ini file: {path}")

    # helper to fetch a section proxy if it exists
    def sec(*names):
        for name in names:
            if cp.has_section(name):
                return cp[name]
        return None

    sect_mstp   = sec("mstp", "MSTP", "BACpypes")
    sect_device = sec("device", "Device", "BACpypes")

    if sect_mstp is None:
        raise KeyError("No [mstp]/[MSTP]/[BACpypes] section found for MS/TP settings in bc.ini")

    # tiny option getter with aliases + casting
    def opt(section, *keys, default=None, cast=None):
        for k in keys:
            if section is not None and section.get(k) is not None:
                val = section.get(k)
                return cast(val) if cast else val
        return default

    # MS/TP transport parameters (map your sample keys)
    mstp = dict(
        _address     = opt(sect_mstp, "_address", "address", "mstp_address", cast=int),
        _interface   = opt(sect_mstp, "_interface", "interface", "port", "serial_port"),
        _baudrate    = opt(sect_mstp, "_baudrate", "baudrate", "baud", cast=int, default=38400),
        _max_masters = opt(sect_mstp, "_max_masters", "max_masters", "maxmasters", cast=int, default=127),
        _maxinfo     = opt(sect_mstp, "_maxinfo", "max_info_frames", "maxinfo", "maxinfoframes", cast=int, default=1),
        _mstp_dir    = opt(sect_mstp, "_mstp_dir", "mstp_dir", "mstp_directory", default="/tmp")
    )
    if mstp["_address"] is None or mstp["_interface"] is None:
        raise KeyError("Missing 'address' or 'interface' in your [BACpypes]/[mstp] section.")

    # Device identity (fall back to [BACpypes] for everything)
    dev = dict(
        objectName            = opt(sect_device, "objectName", "object_name", default="MSTP-Client"),
        objectIdentifier      = opt(sect_device, "objectIdentifier", "device_id", cast=int, default=599),
        maxApduLengthAccepted = opt(sect_device, "maxApduLengthAccepted", "max_apdu", cast=int, default=1024),
        segmentationSupported = opt(sect_device, "segmentationSupported", "segmentation", default="noSegmentation"),
        vendorIdentifier      = opt(sect_device, "vendorIdentifier", "vendor_id", cast=int, default=15),
    )

    return mstp, dev

def _extract_mstp_mac(pdu_source) -> Optional[int]:
    if pdu_source is None:
        return None
    try:
        mac = getattr(pdu_source, "addrAddr", None)
        if mac is not None:
            return int(mac)
    except Exception:
        pass
    try:
        addr_bytes = getattr(pdu_source, "addrAddress", None)
        if addr_bytes:
            return int(addr_bytes[0])
    except Exception:
        pass
    try:
        route = getattr(pdu_source, "addrRoute", None)
        if route:
            return _extract_mstp_mac(route[-1])
    except Exception:
        pass
    m = re.match(r"\s*(\d+)", str(pdu_source))
    return int(m.group(1)) if m else None


# ------------------------- APP / SESSION -------------------------

class _MSTPApp(MSTPSimpleApplication):
    """Application that collects I-Am replies and supports IOCB I/O."""
    def __init__(self, device, address):
        super().__init__(device, address)
        self._iam_queue: Queue = Queue()

    def indication(self, apdu):
        # Capture I-Am (unconfirmed)
        if isinstance(apdu, IAmRequest):
            try:
                dev_type, dev_inst = apdu.iAmDeviceIdentifier
                if dev_type != "device":
                    return
                result = {
                    "device_instance": int(dev_inst),
                    "max_apdu": int(apdu.maxAPDULengthAccepted),
                    "segmentation": str(apdu.segmentationSupported),
                    "vendor_id": int(getattr(apdu, "vendorID")),
                    "source_mac": _extract_mstp_mac(apdu.pduSource),
                }
                self._iam_queue.put(result)
            except Exception:
                pass

        super().indication(apdu)


class _Core:
    """Singleton-like core/session manager so you can call functions repeatedly."""
    _lock = threading.Lock()
    _started = False
    _app: Optional[_MSTPApp] = None

    @classmethod
    def ensure_started(cls, ini_path: str):
        with cls._lock:
            if cls._started:
                return
            mstp, dev = load_bc_ini(ini_path)
            ldo = LocalDeviceObject(**dev, **mstp)
            cls._app = _MSTPApp(ldo, Address(mstp["_address"]))

            enable_sleeping()
            t = threading.Thread(target=run, name="bacpypes-core", daemon=True)
            t.start()
            cls._started = True

    @classmethod
    def app(cls) -> _MSTPApp:
        if not cls._app:
            raise RuntimeError("BACpypes core not started; call ensure_started() first")
        return cls._app


# ------------------------- PUBLIC API -------------------------

def whois(ini_path: str, timeout: float = 3.0,
          dest: Optional[str] = None,
          low_limit: Optional[int] = None,
          high_limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Broadcast (or directed) Who-Is and collect I-Am results for 'timeout' seconds.
    Returns list of unique devices (by device_instance).
    """
    _Core.ensure_started(ini_path)
    app = _Core.app()

    # drain queue before we start (fresh results)
    try:
        while True:
            app._iam_queue.get_nowait()
    except Empty:
        pass

    req = WhoIsRequest()
    if dest:
        req.pduDestination = Address(dest)
    else:
        req.pduDestination = GlobalBroadcast()
    if low_limit is not None and high_limit is not None:
        req.deviceInstanceRangeLowLimit  = int(low_limit)
        req.deviceInstanceRangeHighLimit = int(high_limit)

    @deferred
    def _send():
        app.request(req)

    # collect until timeout
    end = time.time() + float(timeout)
    seen: Dict[int, Dict[str, Any]] = {}
    while time.time() < end:
        try:
            d = app._iam_queue.get(timeout=0.1)
            seen[d["device_instance"]] = d
        except Empty:
            pass
    return list(seen.values())


def iam(ini_path: str) -> Dict[str, Any]:
    """
    Broadcast an I-Am for our local device. Returns {"sent": true} if queued.
    """
    _Core.ensure_started(ini_path)
    app = _Core.app()
    dev = app.localDevice

    req = IAmRequest()
    req.pduDestination = GlobalBroadcast()
    req.iAmDeviceIdentifier   = dev.objectIdentifier
    req.maxAPDULengthAccepted = dev.maxApduLengthAccepted
    req.segmentationSupported = dev.segmentationSupported
    req.vendorID              = dev.vendorIdentifier

    @deferred
    def _send():
        app.request(req)

    return {"sent": True}


def read_property(ini_path: str, addr: int, obj_type: str, obj_inst: int,
         prop: str, index: Optional[int] = None) -> Dict[str, Any]:
    """
    Confirmed ReadProperty to a specific MAC address.
    """
    _Core.ensure_started(ini_path)
    app = _Core.app()

    obj_id = (obj_type, int(obj_inst))
    datatype = get_datatype(obj_type, prop)
    if not datatype:
        return {"error": f"invalid property '{prop}' for object type '{obj_type}'"}

    req = ReadPropertyRequest(objectIdentifier=obj_id, propertyIdentifier=prop)
    req.pduDestination = Address(int(addr))
    if index is not None:
        req.propertyArrayIndex = int(index)

    iocb = IOCB(req)
    app.request_io(iocb)
    iocb.wait()  # block until done

    if iocb.ioError:
        return {"error": str(iocb.ioError)}

    apdu = iocb.ioResponse
    if not isinstance(apdu, ReadPropertyACK):
        return {"error": "no ack"}

    # Determine cast type (array index special-case like in sample)
    dt = get_datatype(apdu.objectIdentifier[0], apdu.propertyIdentifier)
    if not dt:
        return {"error": "unknown datatype"}
    if issubclass(dt, Array) and (apdu.propertyArrayIndex is not None):
        if apdu.propertyArrayIndex == 0:
            val = apdu.propertyValue.cast_out(Unsigned)
        else:
            val = apdu.propertyValue.cast_out(dt.subtype)
    else:
        val = apdu.propertyValue.cast_out(dt)

    # Make it JSON-friendly
    try:
        json.dumps(val)
        out_val = val
    except TypeError:
        out_val = str(val)

    return {
        "address": int(addr),
        "object": {"type": obj_type, "instance": int(obj_inst)},
        "property": prop,
        "index": index,
        "value": out_val,
    }


def write_property(ini_path: str, addr: int, obj_type: str, obj_inst: int,
          prop: str, value: str, index: Optional[int] = None,
          priority: Optional[int] = None) -> Dict[str, Any]:
    """
    Confirmed WriteProperty. 'value' follows the sample's encoding:
      - 'null' for Null
      - For AnyAtomic: '<code>:<val>' where code in {b,u,i,r,d,o,c,bs,date,time,id}
      - For plain atomic types, provide the literal (e.g., '42', '3.14')
    """
    _Core.ensure_started(ini_path)
    app = _Core.app()

    obj_id = (obj_type, int(obj_inst))
    dt = get_datatype(obj_type, prop)
    if not dt:
        return {"error": f"invalid property '{prop}' for object type '{obj_type}'"}

    # parse / cast like the console sample
    enc_val: Any
    try:
        if value == "null":
            enc_val = Null()
        elif issubclass(dt, AnyAtomic):
            code, raw = value.split(":", 1)
            lut = {
                'b': Boolean,
                'u': lambda x: Unsigned(int(x)),
                'i': lambda x: Integer(int(x)),
                'r': lambda x: Real(float(x)),
                'd': lambda x: Double(float(x)),
                'o': OctetString,
                'c': CharacterString,
                'bs': BitString,
                'date': Date,
                'time': Time,
                'id': ObjectIdentifier,
            }
            caster = lut[code]
            enc_val = caster(raw) if callable(caster) else caster(raw)
        elif issubclass(dt, Atomic):
            if dt is Integer or dt is Unsigned:
                enc_val = dt(int(value))
            elif dt is Real or dt is Double:
                enc_val = dt(float(value))
            else:
                enc_val = dt(value)
        elif issubclass(dt, Array) and (index is not None):
            if index == 0:
                enc_val = Integer(value)
            elif issubclass(dt.subtype, Atomic):
                enc_val = dt.subtype(value)
            else:
                return {"error": f"unsupported array subtype for {prop}"}
        else:
            # best effort
            enc_val = dt(value)  # may raise
    except Exception as e:
        return {"error": f"value cast error: {e}"}

    req = WritePropertyRequest(
        objectIdentifier=obj_id,
        propertyIdentifier=prop,
    )
    req.pduDestination = Address(int(addr))
    req.propertyValue = AnyCD()
    try:
        req.propertyValue.cast_in(enc_val)
    except Exception as e:
        return {"error": f"WriteProperty cast_in error: {e}"}
    if index is not None:
        req.propertyArrayIndex = int(index)
    if priority is not None:
        req.priority = int(priority)

    iocb = IOCB(req)
    app.request_io(iocb)
    iocb.wait()

    if iocb.ioError:
        return {"error": str(iocb.ioError)}
    if not isinstance(iocb.ioResponse, SimpleAckPDU):
        return {"error": "no simple ack"}
    return {"ack": True}


def discover(ini_path: str, addr_mac: int, device_id: int, timeout: float = 5.0) -> Dict[str, Any]:
    """
    Walk a device's objectList via repeated ReadProperty requests.
    Returns: {"object_list": [...]} or {"error": "...", "object_list": [...]}
    """
    _Core.ensure_started(ini_path)
    app = _Core.app()

    results: List[Any] = []
    index_queue: List[int] = [0]   # start with index 0 to get count
    state = {"first": True}        # avoid nonlocal scoping issues
    done = threading.Event()
    error_holder: List[str] = []

    def _send_next():
        if not index_queue:
            done.set()
            return

        idx = index_queue.pop(0)
        req = ReadPropertyRequest(
            objectIdentifier=("device", int(device_id)),
            propertyIdentifier="objectList",
        )
        req.pduDestination = Address(int(addr_mac))
        req.propertyArrayIndex = idx

        iocb = IOCB(req)

        def _on_reply(i: IOCB):
            try:
                if i.ioError:
                    error_holder.append(str(i.ioError))
                    done.set(); return

                apdu = i.ioResponse
                if not isinstance(apdu, ReadPropertyACK):
                    error_holder.append("not an ack")
                    done.set(); return

                dt = get_datatype(apdu.objectIdentifier[0], apdu.propertyIdentifier)
                if not dt:
                    error_holder.append("unknown datatype for objectList")
                    done.set(); return

                # array handling: index 0 is count, others are ObjectIdentifier entries
                if issubclass(dt, Array) and (apdu.propertyArrayIndex is not None):
                    if apdu.propertyArrayIndex == 0:
                        count = apdu.propertyValue.cast_out(Unsigned)
                        # enqueue 1..count
                        index_queue[:] = list(range(1, int(count) + 1))
                        state["first"] = False
                    else:
                        value = apdu.propertyValue.cast_out(dt.subtype)
                        results.append(value)
                else:
                    # some stacks return the whole array when no index is given;
                    # we didn't ask for that, but handle gracefully
                    value = apdu.propertyValue.cast_out(dt)
                    # coerce to list of object identifiers if possible
                    try:
                        results.extend(list(value))
                    except Exception:
                        results.append(value)

                # chain the next read
                deferred(_send_next)

            except Exception as e:
                error_holder.append(str(e))
                done.set()

        iocb.add_callback(_on_reply)
        app.request_io(iocb)

    # kick it off
    deferred(_send_next)

    # wait until done or timeout
    if not done.wait(timeout=float(timeout)):
        return {"error": "discover timeout", "object_list": _json_safe(results)}

    if error_holder:
        return {"error": error_holder[0], "object_list": _json_safe(results)}

    return {"object_list": _json_safe(results)}

def _mstp_port_online(port) -> bool:
    """
    Heuristic: consider the port 'online' once it has seen or held the token.
    Adjust these attribute names to match your misty.mstplib port implementation.
    """
    # Common state strings
    state = getattr(port, "state", None)
    if isinstance(state, str) and state in ("USE_TOKEN", "PASS_TOKEN"):
        return True

    # Common booleans
    for flag in ("online", "seen_token", "has_token"):
        val = getattr(port, flag, None)
        if isinstance(val, bool) and val:
            return True

    return False


def _wait_until_online(port, timeout: float = 5.0, poll: float = 0.1) -> bool:
    import time as _time
    deadline = _time.time() + timeout
    while _time.time() < deadline:
        if _mstp_port_online(port):
            return True
        _time.sleep(poll)
    return False

def parse_property_path_for_ids(path: str) -> Tuple[Optional[int], Optional[str], Optional[int]]:
    """
    Extract (deviceId, objectType, objectInstance) from a path like:
      .../devices/<deviceId>/<objectType>/<objectInstance>
    Returns (None, None, None) if not parseable.
    """
    parts = [p for p in path.split("/") if p]
    try:
        i = parts.index("devices")
        device_id = int(parts[i + 1])
        obj_type = parts[i + 2]
        obj_inst = int(parts[i + 3])
        return device_id, obj_type, obj_inst
    except Exception:
        return None, None, None
    
def parse_present_value(obj_type: str, raw_value: Any) -> Any:
    """
    Convert a raw 'presentValue' returned by ReadProperty into a normalized Python value
    according to your bacnet_defines.json entry for obj_type.

    - BOOLEAN: returns bool, mapping 'active'/'inactive', on/off, 1/0, etc.
    - REAL:    returns float
    - INTEGER/UNSIGNED/ENUMERATED: returns int
    - STRING/NONE/UNKNOWN: returns str
    """
    btype = (get_bacnet_type(obj_type) or "UNKNOWN").upper()

    if btype == "BOOLEAN":
        return _to_boolish(raw_value)
    if btype == "REAL":
        # Many devices may still send "23.0" as a string
        return _to_float(raw_value)
    if btype in ("INTEGER", "UNSIGNED", "ENUMERATED"):
        return _to_int(raw_value)
    # STRING, NONE, UNKNOWN, or anything else: stringify
    return _to_str(raw_value)

def encode_present_value_for_write(obj_type: str, value: Any):
    """
    Convert a user/Node value into a WriteProperty 'propertyValue' suitable for BACpypes.


    Special cases:
      - binaryOutput/binaryValue: 'active'/'on'/1/True => True ; 'inactive'/'off'/0/False => False
    """
    if(obj_type == 'binaryOutput'):
        if value == True:
            return 'active'
        if value == False:
            return 'inactive'
    
    return value

