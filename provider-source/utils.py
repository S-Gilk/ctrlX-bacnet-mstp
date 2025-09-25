import os

from ctrlxdatalayer.variant import Variant

def get_type_address(value):
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

def set_env_from_json_object(variableObject):
    for variable in variableObject:
        value = variableObject[variable]
        os.environ[variable] = str(value)
        print(f"Set environment variable {variable} to: {os.environ[variable]}")