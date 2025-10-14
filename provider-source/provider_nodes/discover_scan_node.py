# SPDX-FileCopyrightText: Bosch Rexroth AG
#
# SPDX-License-Identifier: MIT
import json
import threading

import ctrlxdatalayer
from comm.datalayer import NodeClass
from ctrlxdatalayer.provider import Provider
from ctrlxdatalayer.provider_node import (
    ProviderNode,
    ProviderNodeCallbacks,
    NodeCallback,
)
from ctrlxdatalayer.variant import Result, Variant
from ctrlxdatalayer.metadata_utils import (
    MetadataBuilder,
    AllowedOperation,
    ReferenceType
)

from provider_nodes.device_property_node import DevicePropertyNode
from helper.node_manager import track_node

from helper.mstp_services import discover, get_mac_for_device, get_datalayer_type, get_uninitialized_default

from defines import NodeType, ACTIVE_INI_PATH,  is_writable

from utils import get_type_address_from_string, set_variant_value


class DiscoverScanNode:
    """DiscoverScanNode"""

    def __init__(self, provider: Provider, nodeAddress: str):
        """__init__"""
        self._cbs = ProviderNodeCallbacks(
            self.__on_create,
            NotImplemented,
            NotImplemented,
            NotImplemented,
            self.__on_write,
            self.__on_metadata,
        )

        self._providerNode = ProviderNode(self._cbs)
        self._provider = provider
        self._nodeAddress = nodeAddress
        self._metadata = self.create_metadata()

    def create_metadata(self) -> Variant:
        """create_metadata"""
        builder = MetadataBuilder(AllowedOperation.WRITE)
        #builder = builder.set_display_name(self._nodeAddress)
        builder = builder.set_node_class(NodeClass.NodeClass.Method)
        #builder.add_reference(ReferenceType.create(), "types/datalayer/bool8")
        return builder.build()

    def register_node(self):
        """register_node"""
        return self._provider.register_node(self._nodeAddress,
                                            self._providerNode)

    def unregister_node(self):
        """unregister_node"""
        self._provider.unregister_node(self._nodeAddress)
        self._metadata.close()

    def __on_write(
        self,
        userdata: ctrlxdatalayer.clib.userData_c_void_p,
        address: str,
        data: Variant,
        cb: NodeCallback,
    ):
        """__on_write"""
        print(
            "__on_write()",
            "address:",
            address,
            "data:",
            data,
            "userdata:",
            userdata,
            flush=True,
        )

        thread = threading.Thread(target=self.run_property_scan)
        thread.start()
        cb(Result.OK, data)

    def __on_create(
        self,
        userdata: ctrlxdatalayer.clib.userData_c_void_p,
        address: str,
        data: Variant,
        cb: NodeCallback,
    ):
        """__on_create"""
        print("__on_create()",
              "address:",
              address,
              "userdata:",
              userdata,
              flush=True)
        
        thread = threading.Thread(target=self.run_property_scan)
        thread.start()
        cb(Result.OK, data)


    def __on_metadata(
        self,
        userdata: ctrlxdatalayer.clib.userData_c_void_p,
        address: str,
        cb: NodeCallback,
    ):
        """__on_metadata"""
        # print("__on_metadata()", "address:", address, flush=True)
        cb(Result.OK, self._metadata)

        # OPTIMIZAITON --- To speed this up... can cache all of this info on the node as properties
    def run_property_scan(self):
        # Get current datalayer node path and device ID
        # TODO --- Parse address using mstpservices function
        deviceID_s = self._nodeAddress.split('/').pop(-2)
        deviceID = int(deviceID_s)
        # Get MAC from device cache
        mac = get_mac_for_device(deviceID)
        objects = discover(ACTIVE_INI_PATH, mac, deviceID, timeout=5.0)
        print(json.dumps({"discover": objects}))
        for object in objects['object_list']:
            print(object)
            self.provide_object_node(object)

    def provide_object_node(self, object):
            node_heirarchy = self._nodeAddress.split('/')
            # Remove scanNode path
            node_heirarchy.pop(-1)
            separator = "/"
            object_path = separator.join(node_heirarchy)+"/" + str(object[0]) + "/" + str(object[1])
            print(object_path)
            readOnly = not is_writable(object[0], 'presentValue')
            typeAddressString = get_datalayer_type(object[0])  
            typeAddress = get_type_address_from_string(typeAddressString)
            defaultValue = get_uninitialized_default(object[0])
            variant = set_variant_value(defaultValue)
            property_node = DevicePropertyNode(self._provider, object_path ,typeAddress, variant, readOnly)
            result = property_node.register_node() 
            if result != ctrlxdatalayer.variant.Result.OK:
                print("ERROR Registering node " + object_path + " failed with:",
                    result,
                    flush=True)
            else:
                track_node(NodeType.DEVICE_PROPERTY_NODE, property_node)
