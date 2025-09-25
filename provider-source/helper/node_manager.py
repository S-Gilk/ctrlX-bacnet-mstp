from defines import NodeType

datalayerNodes = {
    "configParameterNodes":[],
    "deviceNodes":[],
    "devicePropertyNodes":[],
    "scanNodes":[]
}

def get_type_string_from_enum(type:NodeType):
    match type:
        case NodeType.CONFIG_PARAMETER:
            return "configParameterNodes"
        case NodeType.DEVICE_NODE:
            return "deviceNodes"
        case NodeType.DEVICE_PROPERTY_NODE:
            return "devicePropertyNodes"
        case NodeType.SCAN_NODE:
            return "scanNodes"

def track_node(type:NodeType, node):
    typeString = get_type_string_from_enum(type)
    datalayerNodes[typeString].append(node)

def release_nodes():
    for nodeList in datalayerNodes.values():
        for node in nodeList:
            print(f"Releasing node: {node._nodeAddress}")
            try:
                node.unregister_node()
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
            del node

    