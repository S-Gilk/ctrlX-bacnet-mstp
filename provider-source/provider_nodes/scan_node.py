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

from provider_nodes.device_node import DeviceNode

import subprocess


class ScanNode:
    """ScanNode"""

    def __init__(self, provider: Provider, nodeAddress: str):
        """__init__"""
        self._cbs = ProviderNodeCallbacks(
            NotImplemented,
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

        # Need to call the bacnet-stack scan function here. Maybe bacwi? Wait to return until scan is complete??
        # Example 1: Running a simple command with no arguments
        #subprocess.run(["ls", "-l"]) 

        # Example 2: Running an executable with arguments
        # Replace 'my_executable' with the actual path to your binary
        # and 'arg1', 'arg2' with the desired arguments
        #subprocess.run(["my_executable", "arg1", "arg2"]) 

        # Example 3: Capturing output and errors
        result = subprocess.run(
            ["ls", "-l"], 
            capture_output=True, 
            text=True,  # Decode output as text
            check=True  # Raise CalledProcessError if the command returns a non-zero exit code
        )
        if(result.stdout):
            print("Stdout:", result.stdout)
        if(result.stderr):
            print("Stderr:", result.stderr)

        # 1-Iterate over text output and parse out devices...
        # 2-Provide datalayer nodes for each device ID
        self._provider

        cb(Result.OK, data)

    def __on_metadata(
        self,
        userdata: ctrlxdatalayer.clib.userData_c_void_p,
        address: str,
        cb: NodeCallback,
    ):
        """__on_metadata"""
        print("__on_metadata()", "address:", address, flush=True)
        cb(Result.OK, self._metadata)