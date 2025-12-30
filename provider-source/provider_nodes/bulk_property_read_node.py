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

from helper.mstp_services import get_mac_for_device, parse_device_path_for_id, read_property_multiple

from defines import NodeType, ACTIVE_INI_PATH

from utils import get_type_address_from_string, set_variant_value


class BulkPropertyReadNode:
    """BulkPropertyReadNode"""

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
        builder = MetadataBuilder(AllowedOperation.CREATE)
        #builder = builder.set_display_name(self._nodeAddress)
        builder = builder.set_node_class(NodeClass.NodeClass.Program)
        builder.add_reference(ReferenceType.create(), "types/datalayer/string") # Pass a JSON string with the property nodes required. Device is inherited from parent
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
        
        request_string = data.get_string()
        thread = threading.Thread(target=self.issue_rpm(request_string), daemon=True)
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

    def issue_rpm(self, request_json):
        device_id = parse_device_path_for_id(self._nodeAddress)
        print("Device ID: " + str(device_id), flush=True)
        mac = get_mac_for_device(device_id)
        print("MAC: " + str(mac), flush=True)
        print(request_json, flush=True)
        payload = json.loads(request_json)  # request_json is a string
        response = read_property_multiple(ini_path=ACTIVE_INI_PATH, addr=mac, requests=payload["requests"])

        print(json.dumps(response), flush=True)
        