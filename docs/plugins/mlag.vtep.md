(plugin-mlag-vtep)=
# Combining MLAG redundancy with VXLAN VTEP functionality

VXLAN enables L3 forwarding of L2 network traffic, and MLAG provides network state synchronization to support redundant active-active connectivity. Some designs require the combination of both, i.e. VXLAN endpoints with redundancy such that single device failures do not lead to broken network overlay paths.

Conceptually, VXLAN redundancy requires the allocation of a shared logical VTEP IP address that is common across both MLAG peers. This enables both peers to send and receive VXLAN packets transparently, and if one fails the other can take over. This plugin coordinates the allocation of this logical anycast IP for MLAG peers, across multiple vendors.

## Supported platforms

This plugin supports the following devices (that also support both VXLAN and MLAG)

| Operating system   | Supports MLAG and VXLAN | Supported by mlag.vtep plugin |
| ------------------ | ----------------------- | ----------------------------- |
| Arista EOS         |           ✅            |              ✅               |
| Aruba AOS-CX       |           ✅            |              ❌               |
| Cumulus Linux 4.x  |           ❌            |              ❌               |
| Cumulus 5.x (NVUE) |           ✅            |              ✅               |
| Dell OS10          |           ✅            |              ✅               |
| FRR                |           ❌            |              ❌               |

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Using the Plugin

The plugin is enabled by simply including it in the toplogy:
```
plugin: [ ...., mlag.vtep ]
```

At that point, anycast MLAG VTEPs are automatically enabled for any MLAG pair of devices in the topology. If this is not desired, the plugin can be disabled on a per-node level:
```
nodes:
  node_without_mlag_vtep:
    lag.mlag.vtep: False
```

The MLAG VTEP works for both static VXLAN and EVPN signalled topologies.

### Customizing the address allocation pool

By default, the plugin configures a pool for `10.101.101.0/24` to allocate its /32 IPs from (1 per MLAG pair). If desired, this configuration can be changed:
```
defaults.mlag.vtep.address_pool: 10.99.99.0/24
```

The regular loopback pool is passed as a secondary source to allocate from, should the first pool run out.

### Elaborate example

The integration tests contain an example topology, under `integration/mlag.vtep/01-vxlan-bridging.yml`. This topology presents a combination of *Netlab* features, showcasing multi-vendor:
* VLAN bridging
* OSPFv2
* static VXLAN
* MLAG to Linux hosts with LACP signalled port-channels
* MLAG orphan hosts (single connected)
* this new `mlag.vtep` plugin for logical VTEP redundancy