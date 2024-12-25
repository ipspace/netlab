(plugin-bonding)=
# Host-side Link Bonding

Linux networking has long supported *bonding*, the ability to use multiple links simultaneously. Netlab supports bonding with LACP through the *lag* module,
this plugin adds support for the other bonding modes (that don't require any special configuration on peers)

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Using the Plugin

* Add `plugin: [ bonding ]` to the lab topology.
* Include the **bonding.ifindex** attribute in any links that need to be bonded

### Supported attributes

The plugin adds the following attributes defined at global, node or interface level:
* **bonding.mode** (string, one of active-backup, balance-tlb, or balance-alb) -- the bonding mode to use, default `active-backup`

Additional interface level attributes:
* **bonding.ifindex** (int,mandatory) -- the interface index for the bonding device; links with matching ifindex are bonded together
* **bonding.primary** (bool) -- optional flag to mark this interface as primary, default *False*. If none of the interfaces are marked as `primary`, the selection is left to the Linux default behavior

### Caveats

The plugin uses the `ip` command to create bond devices and add member links; in case of Linux VMs that are not Ubuntu, the plugin attempts to install this command when not available.
This installation uses `apt-get` which may not work on some Linux VMs

## Examples

(active-backup-bonding)=
### Connect a host to a pair of switches using active-backup bonding

```yaml
plugin: [ bonding ]

bonding.mode: active-backup  # Default

vlans:
  v1:

groups:
  _auto_create: True
  hosts:
    members: [ h1 ]
    device: linux
  switches:
    members: [ s1, s2 ]
    module: [ vlan ]

links:
- s1:
  s2:
  vlan.trunk: [ v1 ]

# Bonded interfaces eth1/eth2
- s1:
  h1:
    bonding.ifindex: 1
- s2:
  h1:
    bonding:
      ifindex: 1
      primary: True  # Use this interface as primary
```

Note how there are no bonding specific modules enabled on the switches
