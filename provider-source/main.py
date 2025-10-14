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

from helper.ctrlx_datalayer_helper import get_provider, provide_node
from helper.node_manager import track_node, release_nodes
from appdata.appdata_control import AppDataControl

import utils
from defines import NodeType, ROOT_PATH, ACTIVE_INI_PATH
from helper.mstp_services import mstp_init_only, mstp_shutdown, load_object_type_definitions

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

    # Init appdata
    appdata_control = AppDataControl()
    appdata_control.ensure_storage_location()
    appdata_control.copy_default_appdata()
   
    # Load BACNET object definitions
    load_object_type_definitions()

    # Init MS/TP
    mstp_init_only(ACTIVE_INI_PATH)

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
            nodeAddress = ROOT_PATH + "scanDevices"
            print(f"Providing scan node: {nodeAddress}")
            node = provide_node(provider, nodeAddress, typeAddress=None, nodeType=NodeType.WHO_IS_SCAN_NODE, value=None)
            track_node(NodeType.WHO_IS_SCAN_NODE, node)

            print("INFO Running endless loop...", flush=True)

            while provider.is_connected() and not __close_app:
                time.sleep(1.0)  # Seconds

            if provider.is_connected() == False:
                print("WARNING ctrlX Data Layer Provider is disconnected",
                    flush=True)
            
            mstp_shutdown()
            release_nodes()

            print("Stopping ctrlX Data Layer provider:", end=" ", flush=True)
            result = provider.stop()
            print(result, flush=True)

        # Attention: Doesn't return if any provider or client instance is still running
        stop_ok = datalayer_system.stop(False)
        print("System Stop", stop_ok, flush=True)

if __name__ == "__main__":
    main()