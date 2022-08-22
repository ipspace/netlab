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

| Operating system   | VXLAN<br>bridging |
| ------------------ | :-: |
| Arista EOS         | ✅  |
| Cisco Nexus OS     | ✅  |
| VyOS               | ✅  |
| Dell OS10          | ✅  |
| Nokia SR Linux     | ✅  |

Notes:
* Arista EOS and Cisco Nexus OS implement per-VLAN ingress replication lists
* Dell OS10 requires a IPv4 address for VXLAN.
* Arista EOS seems not able to work with IPv6-only transport.

## Global Parameters

* **vxlan.domain** -- Ingress replication domain. Optional, default: **global**. Use this parameter when you want to build several isolated bridging domains within your lab.
* **vxlan.flooding** -- A mechanism used to implement VXLAN flooding. Optional, default: **static**.
* **vxlan.vlans** -- list of VLANs to be mapped into VXLAN VNIs.  Optional, defaults to all VLANs with **vni** attribute. All VLANs listed in **vxlan.vlans** list must have a **vni** attribute.
* **use_v6_vtep** -- Use the IPv6 Loopback address as VTEP address. To be used on the devices where you need to explicitly set the local VTEP address, or with *static* flooding to generate the flooding list with IPv6 addresses.

The only supported value for **vxlan.flooding** parameter is **static** -- statically configured ingress replication

All global parameters can also be used as node parameters.

## Default Behavior

* All VLANs are mapped into VXLAN VNIs and bridged between VXLAN-enabled nodes.
* Without specifying **vxlan.domain** for individual nodes or groups of nodes, all VXLAN-enabled nodes belong to a single **global** bridging domain.
* VXLAN flooding is implemented with ingress replication. The VXLAN module builds per-VLAN VTEP replication lists for each node. Whether the device configuration uses VLAN-level or global replication lists is an implementation decision.

## Selecting VXLAN-enabled VLANs

You can select VLANs that should be extended with VXLAN transport in two ways:

* Specify a list of VLAN names in **vxlan.vlans** global- or node-level parameters. VLANs specified in that list must be valid VLAN names but do not have to be present on every node.
* Select VLANs based on the presence of **vni** attribute.

You can set the **vni** attribute for individual VLANs, or have it assigned automatically. By default, all global VLANs get a **vni** attribute, and are thus extended over VXLAN transport. This behavior is controlled with **defaults.vlan.auto_vni** global default.

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
