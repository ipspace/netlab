# VXLAN Configuration Module

This configuration module configures VXLAN data plane, VLAN-to-VXLAN mapping, and static head-end replication.

The module supports the following features:

* VLAN-to-VXLAN bridging implementing _VLAN-based Service Interface_ as defined in RFC 7432/RFC 8365.
* Single VXLAN interface per device
* Default loopback address used as the VTEP IP address
* Static per-VLAN or per-node ingress replication
* Mapping a subset of VLANs into VXLAN VNIs

The module requires VLAN module (to set up **vlans** dictionary) and should be used with a routing protocol module to establish VTEP-to-VTEP connectivity.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Platform Support

The following table describes per-platform support of individual VXLAN features:

| Operating system   | VXLAN<br>bridging | Per-VLAN<br>replication | IPv6 VTEP |
| ------------------ | :-: | :-: | :-: |
| Arista EOS         | ✅  | ✅  |  ❌  |
| Cisco CSR 1000v    | ✅  | ✅  |  ❌  |
| Cisco Nexus OS     | ✅  | ✅  |  ❌  |
| Cumulus Linux      | ✅  | ✅  |  ❌  |
| Dell OS10          | ✅  | ✅  |  ❌  |
| FRR                | ✅  | ✅  |  ❌  |
| Nokia SR Linux     | ✅  |  ❌  |  ❌  |
| Nokia SR OS        | ✅  |  ❌  |  ❌  |
| VyOS               | ✅  | ✅  | ✅  |

```{note}
* Nokia SR Linux needs EVPN control plane to enable VXLAN functionality. VXLAN ingress replication lists are built from EVPN Route Type 3 updates.
```

## Global and Node Parameters

* **vxlan.domain** (node or global) -- Ingress replication domain. Optional, default: **global**. Use this parameter when you want to build several isolated bridging domains within your lab.
* **vxlan.flooding** (node or global) -- A mechanism used to implement VXLAN flooding. Optional, default: **static**.
* **vxlan.vlans** (node or global) -- list of VLANs to be mapped into VXLAN VNIs.  When missing, defaults to all VLANs.
* **vxlan.use_v6_vtep** (global) -- Use the IPv6 Loopback address as VTEP address. To be used on the devices where you need to explicitly set the local VTEP address, or with *static* flooding to generate the flooding list with IPv6 addresses.

The only supported value for **vxlan.flooding** parameter is **static** -- statically configured ingress replication

## Module Parameters

The following default parameters influence VNI assignment:

* **vxlan.start_vni**: Specifies the first auto-assigned VNI (default: 100000).

To change the module defaults, set **defaults.vxlan._value_** parameter(s) in lab topology.

## Default Behavior

* All VLANs are mapped into VXLAN VNIs and bridged between VXLAN-enabled nodes.
* Without specifying **vxlan.domain** for individual nodes or groups of nodes, all VXLAN-enabled nodes belong to a single **global** bridging domain.
* VXLAN flooding is implemented with ingress replication. The VXLAN module builds per-VLAN VTEP replication lists for each node. Whether the device configuration uses VLAN-level or global replication lists is an implementation decision.

## Selecting VXLAN-enabled VLANs

Global VLANs that should be extended with VXLAN transport are specified in **vxlan.vlans** global- or node-level list. When that parameter is missing, all VLANs use VXLAN transport.

VLANs specified in the **vxlan.vlans** list must be valid VLAN names, but do not have to be present on every node.

You can also enable a VLAN for VXLAN transport by setting **vni** VLAN parameter to an integer value.

## Auto-Assign VNI

All VLANs specified in the **vxlan.vlans** list will get a **vni** attribute. To disable the auto-assignment for individual VLANs, set **vni** VLAN parameter to an integer value (static VNI) or *False* (no VNI).

For every VLAN, the VXLAN configuration module tries to use `vxlan.start_vni + vlan.id` as the VLAN VNI, and reverts to sequentially-allocated values when that VNI is already in use.

## Building Ingress Replication Lists

The VXLAN module builds ingress replication lists for all nodes with **vxlan.flooding** set to **static**. Each VLAN-specific ingress replication list includes the VTEP IP addresses of all other nodes in the same **vxlan.domain** that have a VLAN with the same **vni** attribute.

All VLAN-specific ingress replication lists are merged into a node-level ingress replication list. Some devices support per-VLAN replication lists while others might use node-level replication list; the only difference is the amount of irrelevant traffic replicated across the VXLAN transport network.

## Example

We want to create a simple two-switch network transporting two VLANs across VXLAN backbone. We have to define the VLANs first:

```
vlans:
  red:
    mode: bridge
  blue:
    mode: bridge
```

Next, we'll define the *switches* and *hosts* groups to simplify node configuration. All switches will run Arista EOS and use VLAN, VXLAN, and OSPF modules.

```
groups:
  hosts:
    members: [ h1, h2, h3, h4 ]
    device: linux
  switches:
    members: [ s1,s2 ]
    device: eos
    module: [ vlan,vxlan,ospf ]
```

We also have to define individual nodes. Please note that we set node parameters (modules and device type) within *switches* and *hosts* groups.

```
nodes: [ h1, h2, h3, h4, s1, s2 ]
```

Finally, we have to define the links in our lab:

```
links:
- h1:
  s1:
    vlan.access: red
- h2:
  s2:
    vlan.access: red
- h3:
  s1:
    vlan.access: blue
- h4:
  s2:
    vlan.access: blue
- s1:
  s2:
```

Please note we did not have to define:

* VLAN tags or VXLAN VNIs
* VLAN-to-VXLAN mappings
* Any other VLAN or VXLAN parameters apart from VLAN names
* IP addresses or routing protocol parameters
