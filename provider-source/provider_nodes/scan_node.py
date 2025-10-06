# SPDX-FileCopyrightText: Bosch Rexroth AG
#
# SPDX-License-Identifier: MIT
import json

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
from defines import ROOT_PATH
from helper.node_manager import track_node

from mstp_services import whois, iam

from defines import NodeType


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

        # WHO-IS / I-AM
        devices = whois(INI, timeout=3.0)
        print(json.dumps({"whois": devices}))

        sent = iam(INI)
        print(json.dumps({"iam": sent}))


        # 1-Iterate over text output and parse out devices...
        # 2-Provide datalayer nodes for each device ID
        for i in range(5):
            path = ROOT_PATH + "devices/" + str(i)
            provide_device_node(self._provider,path)


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


def provide_device_node(provider:Provider, path:str):
    node = DeviceNode(provider, path ,None,None)
    result = node.register_node() 
    if result != ctrlxdatalayer.variant.Result.OK:
        print("ERROR Registering node " + path + " failed with:",
            result,
            flush=True)
    track_node(NodeType.DEVICE_NODE, node)