# Simple Device Inventory Output Module

*devices* output module creates lab devices inventory as a dictionary of hosts in YAML format (default name: *netlab-devices.yml*).

For every lab device, the *devices* output module:

* Adds device-specific group variables (under **defaults.devices._device_.group_vars**) to device data;
* Adds provider-specific group variables (under **defaults.providers._provider_.devices._device_.group_vars**) to device data;
* Renames **mgmt.ip** attribute to **ansible_host** to be consistent with the Ansible inventory naming convention.

The resulting data structure is almost identical to the output of **ansible-inventory** command taking in account group variable inheritance.

A single formatting modifier can be used to modify the information in the device inventory:

* **pools** -- Add addressing pool information as a **all.vars.pools** key.

## Example

Sample lab topology

```
provider: clab
defaults:
  device: eos

nodes:
- name: s1
- name: s2
  device: frr

links:
- s1-s2
```

Resulting *netlab-devices.yml* inventory (created with **[netlab create --devices](../netlab/create.md)**:

```
# Netlab Devices inventory created from ['topology.yml', 'package:topology-defaults.yml']
#
---
s1:
  ansible_become: true
  ansible_become_method: enable
  ansible_connection: network_cli
  ansible_host: clab-X-s1
  ansible_network_os: eos
  ansible_ssh_pass: admin
  ansible_user: admin
  box: ceos:4.25.1F
  device: eos
  hostname: clab-X-s1
  id: 1
  interface_name: eth%d
  kind: ceos
  links:
  - ifindex: 1
    ifname: Ethernet1
    ipv4: 10.1.0.1/30
    linkindex: 1
    name: s1 -> s2
    neighbors:
      s2:
        ifname: eth1
        ipv4: 10.1.0.2/30
    provider_ifname: eth1
    remote_id: 2
    remote_ifindex: 1
    type: p2p
  loopback:
    ipv4: 10.0.0.1/32
  mgmt:
    ifname: Management0
    ipv4: 192.168.121.101
    mac: 08-4F-A9-00-00-01
s2:
  ansible_connection: docker
  ansible_host: clab-X-s2
  ansible_network_os: frr
  box: frrouting/frr:v7.5.0
  device: frr
  hostname: clab-X-s2
  id: 2
  kind: linux
  links:
  - ifindex: 1
    ifname: eth1
    ipv4: 10.1.0.2/30
    linkindex: 1
    name: s2 -> s1
    neighbors:
      s1:
        ifname: Ethernet1
        ipv4: 10.1.0.1/30
    remote_id: 1
    remote_ifindex: 1
    type: p2p
  loopback:
    ipv4: 10.0.0.2/32
  mgmt:
    ifname: eth0
    ipv4: 192.168.121.102
    mac: 08-4F-A9-00-00-02
```
