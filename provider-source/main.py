#!/usr/bin/env python3

# SPDX-FileCopyrightText: Bosch Rexroth AG
#
# SPDX-License-Identifier: MIT

import os
import signal
import sys
import time
import json

import ctrlxdatalayer

from helper.ctrlx_datalayer_helper import get_provider, provide_node, NodeType
from helper.node_manager import track_node, release_nodes

import utils
from defines import ROOT_PATH

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
            node = provide_node(provider, nodeAddress, typeAddress=None, nodeType=NodeType.SCAN_NODE, value=None)
            track_node(NodeType.SCAN_NODE, node)

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

                # Add existing config parameters as nodes
                for key in data:
                    print(f"Key: {key}, Value: {data[key]}")
                    value = data[key]
                    typeAddress = utils.get_type_address(value)
                    variantValue = utils.set_variant_value(data[key])
                    nodeAddress = ROOT_PATH + "config/" + key
                    print(f"Providing configuration parameter node: {nodeAddress}")
                    node = provide_node(provider, nodeAddress ,typeAddress, NodeType.CONFIG_PARAMETER, variantValue)
                    track_node(NodeType.CONFIG_PARAMETER, node)
                
                # Set environment variables for json object
                utils.set_env_from_json_object(data)

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
            
            release_nodes()

            print("Stopping ctrlX Data Layer provider:", end=" ", flush=True)
            result = provider.stop()
            print(result, flush=True)

        # Attention: Doesn't return if any provider or client instance is still running
        stop_ok = datalayer_system.stop(False)
        print("System Stop", stop_ok, flush=True)

if __name__ == "__main__":
    main()