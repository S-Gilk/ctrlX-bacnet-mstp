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
from ctrlxdatalayer.variant import Result, Variant, VariantType
from ctrlxdatalayer.metadata_utils import (
    MetadataBuilder,
    AllowedOperation,
    ReferenceType
)

from provider_nodes.device_property_node import DevicePropertyNode
from provider_nodes.discover_scan_node import DiscoverScanNode
from helper.node_manager import track_node

from helper.mstp_services import whois, cache_device
from defines import NodeType, ACTIVE_INI_PATH, ROOT_PATH
from utils import get_type_address_from_python_value, set_variant_value

# static mapping by field name (from your whois payload)
_FIELD_TO_VARIANT_TYPE = {
    "device_instance": VariantType.UINT32,
    "max_apdu":       VariantType.UINT32,
    "segmentation":   VariantType.STRING,
    "vendor_id":      VariantType.UINT32,
    "source_mac":     VariantType.UINT8,   # MS/TP MAC is 0..255; bump to UINT16 if you ever see >255
}


class WhoIsScanNode:
    """WhoIsScanNode"""

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
        
        thread = threading.Thread(target=self.run_device_scan)
        thread.start()
        
        cb(Result.OK, data)

    def __on_write(
        self,
        userdata: ctrlxdatalayer.clib.userData_c_void_p,
        address: str,
        data: Variant,
        cb: NodeCallback,
    ):
        """__on_create"""
        print("__on_write()",
              "address:",
              address,
              "userdata:",
              userdata,
              flush=True)
        
        thread = threading.Thread(target=self.run_device_scan)
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

    def run_device_scan(self):
            # WHO-IS
            devices = whois(ACTIVE_INI_PATH, timeout=10.0)
            print(json.dumps({"whois": devices}), flush=True)

            # Provide datalayer nodes for each device ID
            for device in devices:
                cache_device(device)
                device_root_path = ROOT_PATH + "devices/" + str(device["device_instance"])
                print(device_root_path, flush=True)
                self.provide_device_nodes(device,device_root_path)


    def provide_device_nodes(self,device:object, device_root_path:str):
        """
        Create read-only Data Layer nodes for the properties returned by whois().
        Expects `device` to have attributes:
        - device_instance: int
        - max_apdu: int
        - segmentation: str
        - vendor_id: int
        - source_mac: Optional[int]
        """

        # Provide device scan node
        scanAddress = device_root_path + "/scanObjects"
        scanNode = DiscoverScanNode(self._provider, scanAddress)
        result = scanNode.register_node()
        if result != ctrlxdatalayer.variant.Result.OK:
            print(
                "ERROR Registering node " + scanAddress + " failed with:",
                result,
                flush=True,
            )
        else:
            track_node(NodeType.DISCOVER_SCAN_NODE, scanNode)
        # build the props dict from whois device structure
        props = {
            "device_instance": device["device_instance"],
            "max_apdu":        device["max_apdu"],
            "segmentation":    device["segmentation"],
            "vendor_id":       device["vendor_id"],
            "source_mac":      device["source_mac"],
        }

        for key, val in props.items():
            # Skip missing/None values (e.g., source_mac may be None if extraction failed)
            if val is None:
                continue
            
            path = f"{device_root_path}/{key}"
            print(path, flush=True)

            # Choose VariantType from our table; fall back to STRING if unknown
            vt = _FIELD_TO_VARIANT_TYPE.get(key, VariantType.STRING)

            # Build a Variant from the Python value
            variant = set_variant_value(val)
            type_address = get_type_address_from_python_value(val)

            # Create a read-only property node
            node = DevicePropertyNode(self._provider, path, type_address, variant, True)
            result = node.register_node()
            if result != ctrlxdatalayer.variant.Result.OK:
                print(
                    "ERROR Registering node " + path + " failed with:",
                    result,
                    flush=True,
                )
            else:
                track_node(NodeType.DEVICE_PROPERTY_NODE, node)