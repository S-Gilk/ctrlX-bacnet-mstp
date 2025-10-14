# SPDX-FileCopyrightText: Bosch Rexroth AG
#
# SPDX-License-Identifier: MIT

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
    ReferenceType,
)

from helper.mstp_services import get_mac_for_device, parse_property_path_for_ids,parse_present_value, encode_present_value_for_write, read_property, write_property
from defines import ACTIVE_INI_PATH
from utils import set_variant_value_by_type, get_variant_value_by_type


class DevicePropertyNode:
    """DevicePropertyNode"""

    def __init__(self, provider: Provider, nodeAddress: str, typeAddress: str,
                 initialValue: Variant, readOnly):
        """__init__"""
        self._cbs = ProviderNodeCallbacks(
            self.__on_create,
            self.__on_remove,
            self.__on_browse,
            self.__on_read,
            self.__on_write,
            self.__on_metadata,
        )

        self._providerNode = ProviderNode(self._cbs)
        self._provider = provider
        self._nodeAddress = nodeAddress
        self._typeAddress = typeAddress
        self._data = initialValue
        if(readOnly):
            allowed=AllowedOperation.READ
        else:
            allowed=AllowedOperation.READ | AllowedOperation.WRITE
        self._metadata = self.create_metadata(allowed)

    def create_metadata(self, allowed) -> Variant:
        """create_metadata"""
        builder = MetadataBuilder(allowed)
        #builder = builder.set_display_name(self._nodeAddress)
        builder = builder.set_node_class(NodeClass.NodeClass.Variable)
        if(allowed & AllowedOperation.READ):
            builder.add_reference(ReferenceType.read(), self._typeAddress)
        if(allowed & AllowedOperation.WRITE):
            builder.add_reference(ReferenceType.write(), self._typeAddress)
        return builder.build()

    def register_node(self):
        """register_node"""
        return self._provider.register_node(self._nodeAddress,
                                            self._providerNode)

    def unregister_node(self):
        """unregister_node"""
        self._provider.unregister_node(self._nodeAddress)
        self._metadata.close()
        self._data.close()

    def set_value(self, value: Variant):
        """set_value"""
        self._data = value

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
        cb(Result.OK, data)

    def __on_remove(
        self,
        userdata: ctrlxdatalayer.clib.userData_c_void_p,
        address: str,
        cb: NodeCallback,
    ):
        """__on_remove"""
        print("__on_remove()",
              "address:",
              address,
              "userdata:",
              userdata,
              flush=True)
        cb(Result.UNSUPPORTED, None)

    def __on_browse(
        self,
        userdata: ctrlxdatalayer.clib.userData_c_void_p,
        address: str,
        cb: NodeCallback,
    ):
        """__on_browse"""
        print("__on_browse()",
              "address:",
              address,
              "userdata:",
              userdata,
              flush=True)
        with Variant() as new_data:
            new_data.set_array_string([])
            cb(Result.OK, new_data)

    def __on_read(
        self,
        userdata: ctrlxdatalayer.clib.userData_c_void_p,
        address: str,
        data: Variant,
        cb: NodeCallback,
    ):
        # """__on_read: fetch presentValue from device each time."""
        # print(
        #     "__on_read()",
        #     "address:",
        #     address,
        #     "data:",
        #     self._data,
        #     "userdata:",
        #     userdata,
        #     flush=True,
        # )


    # Parse identifiers from path
        device_id, object_type, object_instance = parse_property_path_for_ids(address)

        if device_id is None:
            # Path didn't match expected layout; return last known value
            cb(Result.OK, self._data)
            return
        
        mac = get_mac_for_device(device_id)

        if mac is None:
            # Cache not ready; return last known value
            cb(Result.OK, self._data)
            return
    
        # Alwars reading presentValue of property. There are other fields as well (ie. units)
        response = read_property(ACTIVE_INI_PATH, mac, object_type, object_instance, "presentValue")
        # print(response,flush=True)
        raw_value = response['value']
        parsed_value = parse_present_value(object_type, raw_value)
        # print(parsed_value, flush=True)
        variant_type = self._data.get_type()
        set_variant_value_by_type(self._data, variant_type, parsed_value)

        new_data = self._data
        cb(Result.OK, new_data)

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

        if self._data.get_type() != data.get_type():
            cb(Result.TYPE_MISMATCH, None)
            return

        # OPTIMIZATION ---  To speed this up... can cache all of this info on the node as properties
        device_id, object_type, object_instance = parse_property_path_for_ids(address)
        value = get_variant_value_by_type(data, data.get_type())
        encoded_value = encode_present_value_for_write(object_type, value)
        mac = get_mac_for_device(device_id)
        response = write_property(ACTIVE_INI_PATH, mac, object_type, object_instance, "presentValue", encoded_value, priority=8)
        print(response, flush=True)
        
        result, self._data = data.clone()
        cb(Result.OK, self._data)

    def __on_metadata(
        self,
        userdata: ctrlxdatalayer.clib.userData_c_void_p,
        address: str,
        cb: NodeCallback,
    ):
        """__on_metadata"""
        # print("__on_metadata()", "address:", address, flush=True)
        cb(Result.OK, self._metadata)