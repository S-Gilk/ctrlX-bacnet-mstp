from defines import NodeType

datalayerNodes = {
    "discoverNodes":[],
    "devicePropertyNodes":[],
    "whoIsNodes":[],
    "folderNodes":[]
}

def get_type_string_from_enum(type:NodeType):
    match type:
        case NodeType.DISCOVER_SCAN_NODE:
            return "discoverNodes"
        case NodeType.DEVICE_PROPERTY_NODE:
            return "devicePropertyNodes"
        case NodeType.WHO_IS_SCAN_NODE:
            return "whoIsNodes"
        case NodeType.FOLDER_NODE:
            return "folderNodes"

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

    