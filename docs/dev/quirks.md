(dev-device-hooks)=
# Device Quirks and Device Hooks

Individual devices supported by _netlab_ might have implementation details that are not recognized by the _netlab_ core, configuration modules, or device feature flags. These details should be handled by *device quirks* modules.

The device quirks modules can also implement *device hooks* -- device-specific methods that _netlab_ calls at various points of the lab lifecycle (for example, to reload device configuration with *netmiko*).

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Framework

A *device quirks* module must reside in the `netsim/devices` directory and have the same name as the device (example: `eos.py` for Arista EOS).

It must define a descendant of the `_Quirks` class (defined in `netsim/devices/__init__.py`) with the `device_quirks` method:

```
class EOS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
  ...
```

Devices that share most of their quirks (for example, Cisco IOS XR and Cisco 8000v) can inherit the device class from another device module:

```
from .iosxr import IOSXR as _IOSXR

class Cisco8000v(_IOSXR):
  ...
```

_netlab_ loads the device module the first time it needs it and caches the device object in the **DEVICE_MODULE** dictionary.

## Device Quirks

The **device_quirks** method is called for every node at the very end of the data transformation (after the provider **post_transform** hook). When a quirks function modifies node data, the modified data will be used to generate provider configuration files or Ansible inventory.

You should define a new function for every quirk you want to handle, and call those functions from the `device_quirks` method. It probably makes sense to use the **node.module** attribute when deciding which functions to call, for example:

```
class EOS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    if 'evpn' in mods:
      if log.debug_active('quirks'):
        print(f'Arista EOS: Checking MPLS VLAN bundle for {node.name}')
      check_mlps_vlan_bundle(node)
```

The individual quirks functions should check the relevant node data (example: **vlan.mode** must be set to **bridge** on Arista EOS if **vlan.evpn.bundle** is set) and make changes to node data structure if needed (example: remove **Vlan{vlan.id}** interfaces on Arista EOS for VLANs in an EVPN/MPLS VLAN bundle).

Use the **report_quirk** function to report unsupported configurations. It reports an error (or a warning or an info message when you set the **category** parameter or the **info** flag) and tells the user how to disable the check when you specify the **quirk** parameter (the check is skipped when the **defaults.devices._device_.warnings._quirk_** setting is `False`).

The **check_config_sw** method is called before the initial device configuration is deployed (in **netlab up** and **netlab initial**). Use it to check whether the software needed to configure the device (for example, an Ansible collection) is installed. _netlab_ aborts the configuration deployment if a **check_config_sw** method reports an error.

## Device Hooks

A device hook is any method of the device class. _netlab_ calls device hooks with the **exec_device_hook** function (defined in `netsim/devices/__init__.py`):

```
def exec_device_hook(node: Box, topology: Box, method: str, *, debug_flag: str = 'hooks', **kwargs: typing.Any) -> typing.Any
```

The **exec_device_hook** function:

* Loads the device module for the node device
* Checks whether the device class has the specified method. The hook methods do not have to be defined in the `_Quirks` class.
* Calls the method with the **node** and **topology** parameters and any extra keyword parameters specified by the caller, and returns the value returned by the method.
* Returns `None` when the device has no device module or when the device class does not have the specified method.

The extra parameters cannot be checked in advance, so make sure your hook method has the parameters the caller expects. The hook should return a value other than `None` when it did something; the caller can then skip the generic processing. For example, the configuration reload code uses this pattern:

```
if q_devices.exec_device_hook(n_data,topology,'netmiko_reload',conn=conn,nm_data=nm_data) is not None:
  return
```

The device quirks (**device_quirks** and **check_config_sw** methods) are called through the **exec_device_quirk** function, a wrapper around **exec_device_hook** that uses the `quirks` debugging flag.

_netlab_ currently uses these device hooks:

{.table-wrap}
| Hook | Called from | Extra parameters | Meaning |
|------|-------------|------------------|---------|
| **device_quirks** | `netsim.augment.main` | -- | Adjust node data at the end of the data transformation |
| **check_config_sw** | **netlab up**, **netlab initial** | -- | Check whether the software needed to configure the device is installed |
| **netmiko_reload** | **netlab config --reload** | **conn**, **nm_data** | Reload saved device configuration (see [](dev-config-netmiko-reload-hook)) |

## Debugging

* Use the `--debug quirks` CLI parameter to display the device quirks calls
* Use the `--debug hooks` CLI parameter to display the other device hook calls. The debugging printout shows whether _netlab_ found the device module and the hook method.
