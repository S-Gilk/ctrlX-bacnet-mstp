#!/usr/bin/env python3
# BACpypes 0.18.x + Misty MSTP
import configparser, json, re, threading, time
from queue import Queue, Empty
from typing import Any, Dict, List, Optional, Tuple

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

def _get_first(sec, *keys, default=None, cast=None):
    for k in keys:
        if sec and sec.get(k) is not None:
            v = sec.get(k)
            return cast(v) if cast else v
    return default

def load_bc_ini(path: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
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


def read(ini_path: str, addr: int, obj_type: str, obj_inst: int,
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


def write(ini_path: str, addr: int, obj_type: str, obj_inst: int,
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