# Handling Device Quirks

Individual devices supported by _netlab_ might have implementation details that are not recognized by the _netlab_ core, configuration modules, or device feature flags. These details should be handled by *device quirks* modules.

The device quirks are checked at the very end of the data transformation (after provider **post_transform** hook). When a quirks function modifies node data, the modified data will be used to generate provider configuration files or Ansible inventory.

## Framework

A *device quirks* module must reside in `netsim/quirks` directory and have the same name as the device (example: `eos.py` for Arista EOS).

It must define a descendant of the `_Quirks` module with `device_quirks` method:

```
class EOS(_Quirks):

  def device_quirks(self, node: Box, topology: Box) -> None:
  ...
```

You should define a new function for every quirk you want to handle, and call those functions from the `device_quirks` method. It probably makes sense to use **node.module** attribute when deciding which functions to call, for example:

```
class EOS(_Quirks):

  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    if 'evpn' in mods:
      if common.debug_active('quirks'):
        print(f'Arista EOS: Checking MPLS VLAN bundle for {node.name}')
      check_mlps_vlan_bundle(node)
```

The individual quirks functions should check the relevant node data (example: **vlan.mode** must be set to **bridge** on Arista EOS if **vlan.evpn.bundle** is set) and make changes to node data structure if needed (example: remove **Vlan{vlan.id}** interfaces on Arista EOS for VLANs in an EVPN/MPLS VLAN bundle).

Use **common.error** function to report errors that should terminate the data transformation.

