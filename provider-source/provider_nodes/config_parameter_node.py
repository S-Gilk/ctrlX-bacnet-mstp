# SPDX-FileCopyrightText: Bosch Rexroth AG
#
# SPDX-License-Identifier: MIT

# This is a node for configuration parameters. These are linked to environment variables used in the bacnet-stack executables
# OnWrite --- Update config/env.json and set corresponding environment variable

import os
import json

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
    ReferenceType,
)
from utils import set_env_from_json_object


class ConfigParameterNode:
    """ConfigParameterNode"""

    def __init__(self, provider: Provider, nodeAddress: str, typeAddress: str,
                 initialValue: Variant):
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
        self._metadata = self.create_metadata()

    def create_metadata(self) -> Variant:
        """create_metadata"""
        builder = MetadataBuilder(allowed=AllowedOperation.READ
                                  | AllowedOperation.WRITE | AllowedOperation.BROWSE)
        #builder = builder.set_display_name(self._nodeAddress)
        builder = builder.set_node_class(NodeClass.NodeClass.Variable)
        builder.add_reference(ReferenceType.read(), self._typeAddress)
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
        """__on_read"""
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
        
        # Attempt to write to saved configuration file... should've maybe just implemented solutions store plug
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.dirname(current_dir)
        relative_file_path = '/config/env.json'
        path = config_dir + relative_file_path
        try:
            # Open the JSON file in read mode ('r')
            with open(path, 'r') as i:
                # Use json.load() to parse the JSON data directly from the file object
                jsonData = json.load(i)
            # Now 'data' is a Python dictionary containing the JSON content
            keyString = self._nodeAddress.split('/').pop()
            if data.get_type() == VariantType.STRING:
                jsonData[keyString] = data.get_string()
            elif data.get_type() == VariantType.INT32:
                jsonData[keyString] = data.get_int32()
            elif data.get_type() == VariantType.BOOL8:
                jsonData[keyString] = data.get_bool8()
            else:
                raise Exception("Data type not implemented for configuration file.")
            
            with open(path, 'w') as o:
                json.dump(jsonData, o, indent=4) # indent=4 makes the JSON output human-readable
            
            set_env_from_json_object(jsonData)

        except FileNotFoundError:
            print(f"Error: The file '{relative_file_path}' was not found.")
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from '{relative_file_path}'. Check if the file contains valid JSON.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        result, self._data = data.clone()
        cb(Result.OK, self._data)


    def __on_metadata(
        self,
        userdata: ctrlxdatalayer.clib.userData_c_void_p,
        address: str,
        cb: NodeCallback,
    ):
        """__on_metadata"""
        #print("__on_metadata()", "address:", address, flush=True)
        cb(Result.OK, self._metadata)