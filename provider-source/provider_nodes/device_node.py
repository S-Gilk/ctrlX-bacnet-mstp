# SPDX-FileCopyrightText: Bosch Rexroth AG
#
# SPDX-License-Identifier: MIT

# This is a container node for device properties. Don't populate properties unless browsed to

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


class DeviceNode:
    """DeviceNode"""

    def __init__(self, provider: Provider, nodeAddress: str, typeAddress: str,
                 initialValue: Variant):
        """__init__"""
        self._cbs = ProviderNodeCallbacks(
            NotImplemented,
            NotImplemented,
            self.__on_browse,
            NotImplemented,
            NotImplemented,
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
        builder = MetadataBuilder(allowed=AllowedOperation.BROWSE)
        #builder = builder.set_display_name(self._nodeAddress)
        builder = builder.set_node_class(NodeClass.NodeClass.Folder)
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

    def __on_metadata(
        self,
        userdata: ctrlxdatalayer.clib.userData_c_void_p,
        address: str,
        cb: NodeCallback,
    ):
        """__on_metadata"""
        print("__on_metadata()", "address:", address, flush=True)
        cb(Result.OK, self._metadata)