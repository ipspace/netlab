(plugin-mlag-vtep)=
# Combining MLAG Redundancy with VXLAN VTEP Functionality

VXLAN enables L3 forwarding of L2 network traffic, and MLAG provides network state synchronization to support redundant active-active connectivity. Some designs require the combination of both, i.e. VXLAN endpoints with redundancy such that single device failures do not lead to broken network overlay paths.

Conceptually, VXLAN redundancy requires allocating a shared logical VTEP IP address that is common across both MLAG peers. This enables both peers to send and receive VXLAN packets transparently; if one fails, the other can take over. This plugin coordinates the allocation of this logical anycast IP for MLAG peers, across multiple vendors.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Supported Platforms

This plugin works with any device that supports VXLAN and MLAG; it creates an extra loopback interface with 
`vxlan.vtep` set to `True`. It is up to the device configuration templates to render this into a functional VTEP.

## Using the Plugin

To use the plugin, add it to the **plugin** list in the lab topology:

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

## Customizing the Address Allocation Pool

By default, the plugin configures a "mlag_vtep" pool for `10.101.101.0/24` to allocate its /32 IPs from (1 per MLAG pair). If desired, this configuration can be changed:
```
addressing.mlag_vtep.ipv4: 10.99.99.0/24
```

## Sample Topologies

The _netlab_ integration tests include anycast VTEP on an MLAG pair using VXLAN ingress replication and EVPN control plane. 

Both lab topologies use:

* VXLAN transport of bridged VLANs
* Linux hosts dual-attached to the MLAG pair
* Single-attached (orphan) Linux hosts
* OSPFv2 as the core routing protocol and IBGP as the EVPN control-plane protocol
* Multi-vendor VXLAN and EVPN implementation
