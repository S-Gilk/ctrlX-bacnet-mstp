#!/usr/bin/env python3

# SPDX-FileCopyrightText: Bosch Rexroth AG
#
# SPDX-License-Identifier: MIT

import os
import signal
import sys
import time
import json
from enum import Enum

import ctrlxdatalayer
from ctrlxdatalayer.variant import Result, Variant, VariantType

from helper.ctrlx_datalayer_helper import get_provider
from provider_nodes.scan_node import ScanNode
from provider_nodes.device_node import DeviceNode
from provider_nodes.device_property_node import DevicePropertyNode
from provider_nodes.config_parameter_node import ConfigParameterNode

# TODO replace MyProvider nodes with app specific nodes & handlers
    # TODO implement onWrite handler for configuration parameters
# TODO write logic for node provision structure
# TODO write logic for env variable load/save from corresponding datalayer nodes
# --- Load done


class NodeType(Enum):
    CONFIG_PARAMETER = 1
    DEVICE_NODE = 2
    DEVICE_PROPERTY_NODE = 3
    SCAN_NODE = 4

ROOT_PATH = "bacnet/"

__close_app = False


def handler(signum, frame):
    """handler"""
    global __close_app
    __close_app = True
    print('Here you go signum: ', signum, __close_app, flush=True)


def main():
    """main"""
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGABRT, handler)

    with ctrlxdatalayer.system.System("") as datalayer_system:

        datalayerNodes = {
            "configParamaterNodes":[],
            "deviceNodes":[],
            "devicePropertyNodes":[],
            "scanNodes":[]
        }

        datalayer_system.start(False)

        # ip="10.0.2.2", ssl_port=8443: ctrlX COREvirtual with port forwarding and default port mapping
        provider, connection_string = get_provider(datalayer_system,
                                                   ip="10.0.2.2",
                                                   ssl_port=8443)
        if provider is None:
            print("ERROR Connecting", connection_string, "failed.", flush=True)
            sys.exit(1)

        with (
                provider
        ):  # provider.close() is called automatically when leaving with... block
            
            # Provide scan node
            nodeAddress = ROOT_PATH + "scan"
            print(f"Providing scan node: {nodeAddress}")
            node = provide_node(provider, nodeAddress, get_type_address(False), NodeType.SCAN_NODE, set_variant_value(False))
            datalayerNodes["scanNodes"].append(node)
            # Read in config parameters and provide corresponding datalayer nodes
            # Define the path to your JSON file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            relative_file_path = '/config/env.json' 
            try:
                # Open the JSON file in read mode ('r')
                with open(current_dir + relative_file_path, 'r') as file:
                    # Use json.load() to parse the JSON data directly from the file object
                    data = json.load(file)

                # Now 'data' is a Python dictionary containing the JSON content
                print("JSON data loaded successfully:")
                print(data)
                print(f"Type of loaded data: {type(data)}")

                # Add existing config parameters as nodes
                for key in data:
                    print(f"Key: {key}, Value: {data[key]}")
                    value = data[key]
                    typeAddress = get_type_address(value)
                    variantValue = set_variant_value(data[key])
                    nodeAddress = ROOT_PATH + "config/" + key
                    print(f"Providing configuration parameter node: {nodeAddress}")
                    node = provide_node(provider, nodeAddress ,typeAddress, NodeType.CONFIG_PARAMETER, variantValue)
                    datalayerNodes["configParamaterNodes"].append(node)

            except FileNotFoundError:
                print(f"Error: The file '{relative_file_path}' was not found.")
            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON from '{relative_file_path}'. Check if the file contains valid JSON.")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

            print("INFO Running endless loop...", flush=True)

            while provider.is_connected() and not __close_app:
                time.sleep(1.0)  # Seconds

            if provider.is_connected() == False:
                print("WARNING ctrlX Data Layer Provider is disconnected",
                    flush=True)
            
            # Unregister and delete all provided nodes
            for nodeList in datalayerNodes.values():
                for node in nodeList:
                    try:
                        node.unregister_node()
                    except Exception as e:
                        print(f"An unexpected error occurred: {e}")
                    del node

            print("Stopping ctrlX Data Layer provider:", end=" ", flush=True)
            result = provider.stop()
            print(result, flush=True)

        # Attention: Doesn't return if any provider or client instance is still running
        stop_ok = datalayer_system.stop(False)
        print("System Stop", stop_ok, flush=True)

def provide_node(provider: ctrlxdatalayer.provider, nodeAddress: str,
                 typeAddress: str, nodeType:NodeType, value:Variant):
    """provide_node"""

    match nodeType:
        case NodeType.SCAN_NODE:
            node = ScanNode(provider, nodeAddress, typeAddress, value)
        case NodeType.CONFIG_PARAMETER:
            node = ConfigParameterNode(provider, nodeAddress, typeAddress, value)
        case NodeType.DEVICE_NODE:
            node = DeviceNode(provider, nodeAddress, typeAddress, value)
        case NodeType.DEVICE_PROPERTY_NODE:
            node = DevicePropertyNode(provider, nodeAddress, typeAddress, value)
        case _:
            return None
            
    result = node.register_node()
    if result != ctrlxdatalayer.variant.Result.OK:
        print(
            "ERROR Registering node " + nodeAddress + " failed with:",
            result,
            flush=True,
        )

    return node

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

if __name__ == "__main__":
    main()