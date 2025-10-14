import os
from typing import Any, Optional, Type

from ctrlxdatalayer.variant import Variant, VariantType, Result

from bacpypes.constructeddata import Array, SequenceOf

from bacpypes.primitivedata import (
    Null,
    Boolean,
    Unsigned,
    Integer,
    Real,
    Double,
    OctetString,
    CharacterString,
    BitString,
    Enumerated,
    Date,
    Time,
    ObjectIdentifier,
)

def get_type_address_from_python_value(value):
    """get_type_address"""
    typeAddress = None
    if isinstance(value,str):
        typeAddress = "types/datalayer/string"
    elif isinstance(value,bool):
        typeAddress = "types/datalayer/bool8"
    elif isinstance(value,int):
        typeAddress = "types/datalayer/int32"
    elif isinstance(value,float):
        typeAddress = "types/datalayer/float64"
    else:
        print(f"Type address not implemented: {type(value)}")

    return typeAddress

def get_type_address_from_string(typeString):
    """get_type_address"""
    typeAddress = None
    match typeString:
        case 'STRING': typeAddress = "types/datalayer/string"
        case 'BOOL8': typeAddress = "types/datalayer/bool8"
        case 'UINT32': typeAddress = "types/datalayer/uint32"
        case 'FLOAT32': typeAddress = "types/datalayer/float32"
        case _:
            print(f"Type address not implemented: {typeString}")

    return typeAddress

def set_variant_value(value):
    """set_variant_value"""
    variant = Variant()
    if isinstance(value,str):
        variant.set_string(value)
    elif isinstance(value,bool):
        variant.set_bool8(value)
    elif isinstance(value,int):
        variant.set_int32(value)
    elif isinstance(value,float):
        variant.set_float64(value)
    else:
        print(f"Data type not implemented: {type(value)}")

    return variant

def get_variant_value_by_type(variant: Variant, variant_type: VariantType):
    """
    Returns the Variant's value as a native Python object based on the provided VariantType.

    Scalars:
      BOOL8 -> bool
      INT*/UINT* -> int
      FLOAT* -> float
      STRING -> str | None
      TIMESTAMP -> datetime.datetime  (FILETIME converted)

    Arrays:
      ARRAY_* -> list[...] of the scalar type above
      ARRAY_OF_TIMESTAMP -> list[datetime.datetime]

    Binary:
      FLATBUFFERS -> bytearray
      RAW -> bytearray

    Falls back to .get_string() for unknown types.
    """
    if variant is None or variant_type is None:
        return None

    try:
        match variant_type:
            # --- scalars ---
            case VariantType.BOOL8:
                return variant.get_bool8()
            case VariantType.INT8:
                return variant.get_int8()
            case VariantType.UINT8:
                return variant.get_uint8()
            case VariantType.INT16:
                return variant.get_int16()
            case VariantType.UINT16:
                return variant.get_uint16()
            case VariantType.INT32:
                return variant.get_int32()
            case VariantType.UINT32:
                return variant.get_uint32()
            case VariantType.INT64:
                return variant.get_int64()
            case VariantType.UINT64:
                return variant.get_uint64()
            case VariantType.FLOAT32:
                return variant.get_float32()
            case VariantType.FLOAT64:
                return variant.get_float64()
            case VariantType.STRING:
                return variant.get_string()
            case VariantType.TIMESTAMP:
                # Variant already exposes datetime conversion
                return variant.get_datetime()

            # --- arrays ---
            case VariantType.ARRAY_BOOL8:
                return variant.get_array_bool8()
            case VariantType.ARRAY_INT8:
                return variant.get_array_int8()
            case VariantType.ARRAY_UINT8:
                return variant.get_array_uint8()
            case VariantType.ARRAY_INT16:
                return variant.get_array_int16()
            case VariantType.ARRAY_UINT16:
                return variant.get_array_uint16()
            case VariantType.ARRAY_INT32:
                return variant.get_array_int32()
            case VariantType.ARRAY_UINT32:
                return variant.get_array_uint32()
            case VariantType.ARRAY_INT64:
                return variant.get_array_int64()
            case VariantType.ARRAY_UINT64:
                # Note: for timestamps prefer ARRAY_OF_TIMESTAMP below
                return variant.get_array_uint64()
            case VariantType.ARRAY_FLOAT32:
                return variant.get_array_float32()
            case VariantType.ARRAY_FLOAT64:
                return variant.get_array_float64()
            case VariantType.ARRAY_STRING:
                return variant.get_array_string()
            case VariantType.ARRAY_OF_TIMESTAMP:
                # Convenience: list[datetime.datetime]
                return variant.get_array_datetime()

            # --- binary payloads ---
            case VariantType.FLATBUFFERS:
                return variant.get_flatbuffers()
            case VariantType.RAW:
                return variant.get_data()

            # --- unknown/fallback ---
            case _:
                # Best-effort string conversion to avoid exceptions
                return variant.get_string()
    except Exception:
        # On any conversion issue, return None so callers can handle gracefully
        return None
    
def set_variant_value_by_type(variant: Variant, variant_type: VariantType, value) -> Result:
    """
    Sets the given Variant's value based on its VariantType.

    Args:
        variant (Variant): Target variant object.
        variant_type (VariantType): Type to set.
        value: Python value to assign.

    Returns:
        Result: Status of the function call (Result.OK, Result.TYPE_MISMATCH, etc.)
    """
    if variant is None or variant_type is None:
        return Result.MISSING_ARGUMENT

    try:
        match variant_type:
            case VariantType.BOOL8:
                return variant.set_bool8(bool(value))
            case VariantType.INT8:
                return variant.set_int8(int(value))
            case VariantType.UINT8:
                return variant.set_uint8(int(value))
            case VariantType.INT16:
                return variant.set_int16(int(value))
            case VariantType.UINT16:
                return variant.set_uint16(int(value))
            case VariantType.INT32:
                return variant.set_int32(int(value))
            case VariantType.UINT32:
                return variant.set_uint32(int(value))
            case VariantType.INT64:
                return variant.set_int64(int(value))
            case VariantType.UINT64:
                return variant.set_uint64(int(value))
            case VariantType.FLOAT32:
                return variant.set_float32(float(value))
            case VariantType.FLOAT64:
                return variant.set_float64(float(value))
            case VariantType.STRING:
                return variant.set_string(str(value))
            case VariantType.TIMESTAMP:
                return variant.set_timestamp(int(value))
            case VariantType.ARRAY_BOOL8:
                return variant.set_array_bool8(list(value))
            case VariantType.ARRAY_INT32:
                return variant.set_array_int32(list(value))
            case VariantType.ARRAY_UINT32:
                return variant.set_array_uint32(list(value))
            case VariantType.ARRAY_FLOAT32:
                return variant.set_array_float32(list(value))
            case VariantType.ARRAY_FLOAT64:
                return variant.set_array_float64(list(value))
            case VariantType.ARRAY_STRING:
                return variant.set_array_string(list(map(str, value)))
            case VariantType.ARRAY_TIMESTAMP | VariantType.ARRAY_OF_TIMESTAMP:
                return variant.set_array_timestamp(list(value))
            case _:
                # Fallback: attempt to stringify unknown types
                return variant.set_string(str(value))
    except Exception as e:
        print(f"[Variant Setter] Error setting {variant_type.name}: {e}")
        return Result.INVALID_VALUE

def set_env_from_json_object(variableObject):
    for variable in variableObject:
        value = variableObject[variable]
        os.environ[variable] = str(value)
        print(f"Set environment variable {variable} to: {os.environ[variable]}")


def _int_width(v: int, signed: bool) -> VariantType:
    """Choose a VariantType width by value range."""
    if signed:
        if -128 <= v <= 127: return VariantType.INT8
        if -32768 <= v <= 32767: return VariantType.INT16
        if -2147483648 <= v <= 2147483647: return VariantType.INT32
        return VariantType.INT64
    else:
        if 0 <= v <= 255: return VariantType.UINT8
        if 0 <= v <= 65535: return VariantType.UINT16
        if 0 <= v <= 4294967295: return VariantType.UINT32
        return VariantType.UINT64
    
def _array_variant_of(elem_vt: VariantType) -> VariantType:
    mapping = {
        VariantType.BOOL8: VariantType.ARRAY_BOOL8,
        VariantType.INT8: VariantType.ARRAY_INT8,
        VariantType.UINT8: VariantType.ARRAY_UINT8,
        VariantType.INT16: VariantType.ARRAY_INT16,
        VariantType.UINT16: VariantType.ARRAY_UINT16,
        VariantType.INT32: VariantType.ARRAY_INT32,
        VariantType.UINT32: VariantType.ARRAY_UINT32,
        VariantType.INT64: VariantType.ARRAY_INT64,
        VariantType.UINT64: VariantType.ARRAY_UINT64,
        VariantType.FLOAT32: VariantType.ARRAY_FLOAT32,
        VariantType.FLOAT64: VariantType.ARRAY_FLOAT64,
        VariantType.STRING: VariantType.ARRAY_STRING,
        VariantType.TIMESTAMP: VariantType.ARRAY_OF_TIMESTAMP,
    }
    return mapping.get(elem_vt, VariantType.RAW)

def dl_variant_type_from_bacnet(dtype, value: Optional[Any] = None) -> VariantType:
    """
    Map a BACpypes datatype class (preferred) or a decoded Python value to VariantType.
    - Pass `dtype` from bacpypes.object.get_datatype(obj_type, prop_id) when you have it.
    - Also pass `value` if you want width-sensitive choices (e.g., INT16 vs INT32).
    """
    # If dtype is a BACpypes class, match on it first
    if dtype is Boolean:
        return VariantType.BOOL8

    if dtype in (Integer,):
        # choose width by actual value if provided; default to INT32
        if isinstance(value, int):
            return _int_width(value, signed=True)
        return VariantType.INT32

    if dtype in (Unsigned,):
        if isinstance(value, int):
            return _int_width(value, signed=False)
        return VariantType.UINT32

    if dtype is Real:
        return VariantType.FLOAT32

    if dtype is Double:
        return VariantType.FLOAT64

    if dtype in (CharacterString,):
        return VariantType.STRING

    if dtype in (OctetString, BitString):
        return VariantType.RAW

    if dtype in (Enumerated,):
        # enums are integers under the hood; keep as UINT32 (labels can be metadata)
        return VariantType.UINT32

    if dtype in (Date, Time):
        # If you later combine Date+Time into a single BACnet Timestamp, map to TIMESTAMP
        return VariantType.STRING

    if dtype in (ObjectIdentifier,):
        # Could pack (type, instance) into UINT32; string is safer for interop
        return VariantType.STRING

    if dtype in (Array, SequenceOf):
        # If you have the element type and/or actual list values, try to infer homogeneous VT
        if isinstance(value, (list, tuple)) and value:
            # infer from first non-None element
            first = next((x for x in value if x is not None), None)
            if first is None:
                return VariantType.ARRAY_STRING
            elem_vt = dl_variant_type_from_bacnet(type(first), first)
            return _array_variant_of(elem_vt)
        # no element info → raw array of bytes/strings
        return VariantType.ARRAY_STRING

    if dtype in (Null,):
        # choose something benign; string "null" is easy to carry
        return VariantType.STRING
    
    # Fallback
    return VariantType.RAW

def python_type_from_bacnet(dtype: Type[Any]) -> Type[Any]:
    """
    Convert a BACpypes datatype class (from get_datatype) to a native Python type.
    """
    if dtype is None:
        return object  # unknown or proprietary

    # Primitive data types
    if dtype is Null:
        return type(None)
    if dtype is Boolean:
        return bool
    if dtype in (Unsigned, Integer, Enumerated):
        return int
    if dtype in (Real, Double):
        return float
    if dtype in (CharacterString, OctetString, BitString, ObjectIdentifier):
        return str
    if dtype in (Date, Time):
        return str  # represent as ISO date/time strings
    if dtype in (Array, SequenceOf):
        return list  # generic container type for lists/arrays

    # Fallback for unrecognized / vendor-specific
    return object

def variant_type_from_device_field(field: str) -> VariantType:
    mapping = {
        "device_instance": VariantType.UINT32,
        "max_apdu": VariantType.UINT32,
        "segmentation": VariantType.STRING,
        "vendor_id": VariantType.UINT32,
        "source_mac": VariantType.UINT8,
    }
    return mapping.get(field, VariantType.UNKNON)