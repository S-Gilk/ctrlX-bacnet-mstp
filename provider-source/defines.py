# SPDX-License-Identifier: MIT

from enum import Enum

ROOT_PATH = "bacnet/"
DEFAULT_INI_PATH = "bc.ini"
DEFAULT_BACNET_DEFINES_PATH="bacnet_defines.json"
ACTIVE_INI_PATH = "/var/snap/ctrlx-bacnet-mstp/common/solutions/activeConfiguration/BACnet/bc.ini" 
ACTIVE_BACNET_DEFINES_PATH = "/var/snap/ctrlx-bacnet-mstp/common/solutions/activeConfiguration/BACnet/bacnet_defines.json" 

class NodeType(Enum):
    CONFIG_PARAMETER = 1
    DEVICE_PROPERTY_NODE = 2
    WHO_IS_SCAN_NODE = 3
    DISCOVER_SCAN_NODE = 4
    FOLDER_NODE = 5


# This should be exposed in the config
"""
BACnet Standard Object Property Access Map
------------------------------------------
Defines read/write permissions for common BACnet object types
based on ASHRAE 135-2016 (Clause 12, Annex L).

Usage:
    from defines import BACNET_OBJECT_PROPERTIES

    # Example:
    access = BACNET_OBJECT_PROPERTIES["analogInput"]["presentValue"]
    if access == "R/W":
        allowed = AllowedOperation.READWRITE
"""

BACNET_OBJECT_PROPERTIES = {
    # 12.11
    "analogInput": {
        "objectIdentifier": "R",
        "objectName": "R/W",
        "objectType": "R",
        "presentValue": "R",
        "statusFlags": "R",
        "eventState": "R",
        "outOfService": "R/W",
        "units": "R",
        "description": "R/W",
    },

    # 12.12
    "analogOutput": {
        "objectIdentifier": "R",
        "objectName": "R/W",
        "objectType": "R",
        "presentValue": "R/W",
        "statusFlags": "R",
        "eventState": "R",
        "outOfService": "R/W",
        "units": "R",
        "priorityArray": "R",
        "relinquishDefault": "R/W",
        "description": "R/W",
    },

    # 12.13
    "analogValue": {
        "objectIdentifier": "R",
        "objectName": "R/W",
        "objectType": "R",
        "presentValue": "R/W",
        "statusFlags": "R",
        "eventState": "R",
        "outOfService": "R/W",
        "units": "R",
        "priorityArray": "R",
        "relinquishDefault": "R/W",
        "description": "R/W",
    },

    # 12.14
    "binaryInput": {
        "objectIdentifier": "R",
        "objectName": "R/W",
        "objectType": "R",
        "presentValue": "R",
        "statusFlags": "R",
        "eventState": "R",
        "polarity": "R",
        "outOfService": "R/W",
        "inactiveText": "R/W",
        "activeText": "R/W",
        "description": "R/W",
    },

    # 12.15
    "binaryOutput": {
        "objectIdentifier": "R",
        "objectName": "R/W",
        "objectType": "R",
        "presentValue": "R/W",
        "statusFlags": "R",
        "eventState": "R",
        "polarity": "R",
        "outOfService": "R/W",
        "inactiveText": "R/W",
        "activeText": "R/W",
        "priorityArray": "R",
        "relinquishDefault": "R/W",
        "description": "R/W",
    },

    # 12.16
    "binaryValue": {
        "objectIdentifier": "R",
        "objectName": "R/W",
        "objectType": "R",
        "presentValue": "R/W",
        "statusFlags": "R",
        "eventState": "R",
        "outOfService": "R/W",
        "inactiveText": "R/W",
        "activeText": "R/W",
        "priorityArray": "R",
        "relinquishDefault": "R/W",
        "description": "R/W",
    },

    # 12.17
    "multistateValue": {
        "objectIdentifier": "R",
        "objectName": "R/W",
        "objectType": "R",
        "presentValue": "R/W",
        "statusFlags": "R",
        "eventState": "R",
        "outOfService": "R/W",
        "numberOfStates": "R",
        "stateText": "R/W",
        "priorityArray": "R",
        "relinquishDefault": "R/W",
        "description": "R/W",
    },

    # 12.18
    "accumulator": {
        "objectIdentifier": "R",
        "objectName": "R/W",
        "objectType": "R",
        "presentValue": "R",
        "scale": "R",
        "units": "R",
        "prescale": "R/W",
        "maxPresValue": "R",
        "statusFlags": "R",
        "eventState": "R",
        "outOfService": "R/W",
        "description": "R/W",
    },
}

# Convenience helper
def is_writable(obj_type: str, prop: str) -> bool:
    """Return True if property is writable per standard table."""
    return BACNET_OBJECT_PROPERTIES.get(obj_type, {}).get(prop) == "R/W"

