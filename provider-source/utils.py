import os

def set_env_from_json_object(variableObject):
    for variable in variableObject:
        value = variableObject[variable]
        os.environ[variable] = str(value)
        print(f"Set environment variable {variable} to: {os.environ[variable]}")