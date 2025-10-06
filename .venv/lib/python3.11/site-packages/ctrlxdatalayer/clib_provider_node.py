import ctypes

import ctrlxdatalayer
from ctrlxdatalayer.clib import (C_DLR_RESULT, address_c_char_p,
                                 userData_c_void_p)
from ctrlxdatalayer.clib_variant import C_DLR_VARIANT

# ===================================================================
# provider_node.h
# ===================================================================

# typedef void *DLR_PROVIDER_NODE;
C_DLR_PROVIDER_NODE = ctypes.c_void_p

# typedef void *DLR_PROVIDER_NODE_CALLBACKDATA
# _CNodeCallbackData = ctypes.c_void_p
C_DLR_PROVIDER_NODE_CALLBACKDATA = ctypes.c_void_p

# typedef void(*DLR_PROVIDER_NODE_CALLBACK)(DLR_PROVIDER_NODE_CALLBACKDATA callbackdata, DLR_RESULT result, const DLR_VARIANT data);
# _CNodeCallback = ctypes.CFUNCTYPE(None, _CNodeCallbackData, C_DLR_RESULT, C_DLR_VARIANT)
C_DLR_PROVIDER_NODE_CALLBACK = ctypes.CFUNCTYPE(
    None, C_DLR_PROVIDER_NODE_CALLBACKDATA, C_DLR_RESULT, C_DLR_VARIANT)

# typedef DLR_RESULT(*DLR_PROVIDER_NODE_FUNCTION) (void* userData, const char* address, DLR_PROVIDER_NODE_CALLBACK callback, DLR_PROVIDER_NODE_CALLBACKDATA callbackdata);
# _CNodeFunction = ctypes.CFUNCTYPE(C_DLR_RESULT, _CUserdata, _CAddress, C_DLR_PROVIDER_NODE_CALLBACK, _CNodeCallbackData)
C_DLR_PROVIDER_NODE_FUNCTION = ctypes.CFUNCTYPE(
    C_DLR_RESULT, userData_c_void_p, address_c_char_p, C_DLR_PROVIDER_NODE_CALLBACK, C_DLR_PROVIDER_NODE_CALLBACKDATA)

# typedef DLR_RESULT(*DLR_PROVIDER_NODE_FUNCTION_DATA)(void* userData, const char* address, DLR_VARIANT data, DLR_PROVIDER_NODE_CALLBACK callback, DLR_PROVIDER_NODE_CALLBACKDATA callbackdata);
# _CNodeFunctionData = ctypes.CFUNCTYPE(C_DLR_RESULT, _CUserdata, _CAddress, C_DLR_VARIANT, C_DLR_PROVIDER_NODE_CALLBACK, _CNodeCallbackData)
C_DLR_PROVIDER_NODE_FUNCTION_DATA = ctypes.CFUNCTYPE(
    C_DLR_RESULT, userData_c_void_p, address_c_char_p, C_DLR_VARIANT, C_DLR_PROVIDER_NODE_CALLBACK, C_DLR_PROVIDER_NODE_CALLBACKDATA)

# typedef struct DLR_PROVIDER_NODE_CALLBACKS

# typedef void* DLR_SUBSCRIPTION
C_DLR_SUBSCRIPTION = ctypes.c_void_p
# typedef DLR_RESULT(*DLR_PROVIDER_SUBSCRIPTION_FUNCTION)(void * userData, DLR_SUBSCRIPTION subscription, const char * address)
C_DLR_PROVIDER_SUBSCRIPTION_FUNCTION = ctypes.CFUNCTYPE(
    C_DLR_RESULT, userData_c_void_p, C_DLR_SUBSCRIPTION, address_c_char_p)


class C_DLR_PROVIDER_NODE_CALLBACKS(ctypes.Structure):
    """ DLR_PROVIDER_NODE_CALLBACKS """
    _fields_ = [
        ("userData", userData_c_void_p),
        ("onCreate", C_DLR_PROVIDER_NODE_FUNCTION_DATA),
        ("onRemove", C_DLR_PROVIDER_NODE_FUNCTION),
        ("onBrowse", C_DLR_PROVIDER_NODE_FUNCTION),
        ("onRead", C_DLR_PROVIDER_NODE_FUNCTION_DATA),
        ("onWrite", C_DLR_PROVIDER_NODE_FUNCTION_DATA),
        ("onMetadata", C_DLR_PROVIDER_NODE_FUNCTION),
        ("onSubscribe", C_DLR_PROVIDER_SUBSCRIPTION_FUNCTION),
        ("onUnsubscribe", C_DLR_PROVIDER_SUBSCRIPTION_FUNCTION)
    ]


# provider_node
ctrlxdatalayer.clib.libcomm_datalayer.DLR_providerNodeCreate.argtypes = (
    C_DLR_PROVIDER_NODE_CALLBACKS,)
ctrlxdatalayer.clib.libcomm_datalayer.DLR_providerNodeCreate.restype = C_DLR_PROVIDER_NODE

ctrlxdatalayer.clib.libcomm_datalayer.DLR_providerNodeDelete.argtypes = (
    C_DLR_PROVIDER_NODE,)
ctrlxdatalayer.clib.libcomm_datalayer.DLR_providerNodeDelete.restype = None

# subscription.h;
class C_DLR_NOTIFY_ITEM(ctypes.Structure):
    """ NotifyItem """
    _fields_ = [('data', C_DLR_VARIANT),        #// data of the notify item
                ('info', C_DLR_VARIANT)]        #// containing notify_info.fbs (address, timestamp, type, ...)

#//! Publishes new data for this subscription
#//! @param[in] subscription   Reference to the subscription
#//! @param[in] status         Status of notification. On failure subscription is canceled for all items.
#//! @param[in] items          Notification items
#//! @return result
ctrlxdatalayer.clib.libcomm_datalayer.DLR_SubscriptionPublish.argtypes = [
    C_DLR_SUBSCRIPTION, C_DLR_RESULT, ctypes.POINTER(C_DLR_NOTIFY_ITEM), ctypes.c_size_t 
    ]
ctrlxdatalayer.clib.libcomm_datalayer.DLR_SubscriptionPublish.restype = C_DLR_RESULT
      
# //! Returns properties of subscription
# //! @ param[ in ] subscription   Reference to the subscription
# //! @ return Properties of Subscription in a Variant(see sub_properties.fbs)
# DLR_VARIANT DLR_SubscriptionGetProps(DLR_SUBSCRIPTION subscription)
ctrlxdatalayer.clib.libcomm_datalayer.DLR_SubscriptionGetProps.argtypes = [
    C_DLR_SUBSCRIPTION ]
ctrlxdatalayer.clib.libcomm_datalayer.DLR_SubscriptionGetProps.restype = C_DLR_VARIANT

# //! Returns current timestamp
# //! @ param[ in ] subscription   Reference to the subscription
# //! @ return timestamp
ctrlxdatalayer.clib.libcomm_datalayer.DLR_SubscriptionGetTimestamp.argtypes = [
    C_DLR_SUBSCRIPTION ]
ctrlxdatalayer.clib.libcomm_datalayer.DLR_SubscriptionGetTimestamp.restype = ctypes.c_uint64

# //! Returns nodes subscribed for this subscription
# //! @ param[ in ] subscription   Reference to the subscription
# //! @ param[out] nodes         Subscribed nodes as array of strings
# void DLR_SubscriptionGetNodes(DLR_SUBSCRIPTION subscription, DLR_VARIANT nodes)
ctrlxdatalayer.clib.libcomm_datalayer.DLR_SubscriptionGetNodes.argtypes = [
    C_DLR_SUBSCRIPTION, C_DLR_VARIANT ]
ctrlxdatalayer.clib.libcomm_datalayer.DLR_SubscriptionGetNodes.restype = None
