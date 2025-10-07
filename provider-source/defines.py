from enum import Enum

ROOT_PATH = "bacnet/"

INI_PATH = "/var/snap/ctrlx-bacnet-mstp/common/solutions/activeConfiguration/BACnet/bc.ini" 

class NodeType(Enum):
    CONFIG_PARAMETER = 1
    DEVICE_NODE = 2
    DEVICE_PROPERTY_NODE = 3
    SCAN_NODE = 4
