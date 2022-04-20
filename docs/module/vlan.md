# VLANs

The VLAN configuration module implements VLANs and VLAN-related interfaces. Initial implementation supports:

* Access VLANs
* VLAN interfaces (integrated routing and bridging)
* Bridging-only VLANs

The following features are currently _on the radar_:

* Routed subinterfaces
* Access and trunk ports
* Native VLAN

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Platform Support

VLANs are supported on these platforms:

| Operating system      | Access<br>VLANs | VLAN<br>interfaces | Routed<br>subinterfaces | Trunk<br>ports | Native<br>VLAN |
| --------------------- | :-: | :-: |:-: | :-: | :-: |
| Arista EOS            | ✅  | ✅  | ❌   | ❌   | ❌   |
| Cisco IOSv            | ✅  | ✅  | ❌   | ❌   | ❌   |

## VLAN Connectivity Model

The VLAN configuration module assumes you're creating a sane design in which:

* VLAN numbers are globally unique (you're not reusing 802.1q values)
* Every VLAN is contiguous and might span multiple physical links (please note that VLANs bridged across VXLAN or MPLS are still contiguous)
* Every VLAN uses a unique IP subnet across all physical links where it's used.

It might be possible to build topologies that deviate from these rules, but don't be surprised when the results look weird.

## Parameters

The following parameters can be set globally or per node:

* **vlans**: A dictionary of VLAN definitions (see below)
* **vlan.mode**: The default VLAN forwarding mode (<!-- **route**, -->**bridge** or **irb**).
* **vlan.start_vlan_id**: This global value specifies the first auto-assigned VLAN ID (default: 1000).
* **vlan.start_vni**: This global value specifies the first auto-assigned VNI (default: 1000).

(module-vlan-definition)=
## VLAN Definition

VLANs are defined in a global- or node-specific **vlans** dictionary, allowing you to create network-wide VLANs or local VLANs.

```{warning}
Do not reuse VLAN names when defining node-specific VLANs. There's a subtle interaction between global- and node-specific VLANs.
```

The keys of the **vlans** dictionary are VLAN names, the values are VLAN definitions. A VLAN definition could be empty or a dictionary with one or more of these attributes:

* **id** -- 802.1q VLAN tag
* **vni** -- VXLAN VNI
* **vrf** -- the VRF VLAN belongs to
* **prefix** -- IP prefix assigned to the VLAN. The value of the prefix could be an IPv4 prefix or a dictionary with **ipv4** and **ipv6** keys.
* **pool** -- addressing pool used to assign IPv4/IPv6 prefixes to the VLAN. VLAN prefixes are allocated from addressing pools before interface address assignments.

Empty VLAN definition will get [default values](default-vlan-values) assigned during the topology transformation process.

(default-vlan-values)=
## Default VLAN Values

VLAN definitions without **id** or **vni** attribute will get a VLAN ID or VNI assigned automatically. The first auto-assigned VLAN ID is specified in the **vlan.start_id** global attribute; ID assignment process skips IDs assigned to existing VLANs.

(module-vlan-interface)=
## Using VRFs on Interfaces and Links

To use a VLAN on a link, add **vlan** dictionary to a link or an interface on a link. The VLAN dictionary may contain the following attributes:

* **access** -- the name of access VLAN configured on the link or interface

<!--
* **native** -- the name of native VLAN configured on a trunk port
* **mode** -- the default VLAN forwarding mode (route/bridge/irb) for this link or interface -- overrides the node- or global forwarding mode
* **trunk** -- a list or dictionary of VLANs configured on a trunk port

Use a list of VLANs in a **trunk** attribute when you don't want to change individual VLAN attributes on a link/interface level. Use a **trunk** dictionary when you want to set forwarding mode or IPv4/IPv6 addresses for individual VLAN interfaces or routed subinterfaces.

A VLAN within a **trunk** dictionary can have these attributes:

* **mode** -- forwarding mode (route/bridge/irb)
* **ipv4** -- IPv4 address to use on VLAN interface or routed subinterface
* **ipv6** -- IPv6 address to use on VLAN interface or routed subinterface
-->

### Access VLAN Restrictions

To keep the VLAN complexity manageable, the VLAN configuration module enforces these rules:

* Access VLAN defined with link **vlan.access** attribute applies to every attached node that uses **vlan** configuration module.
* Access VLANs defined with interface **vlan.access** attribute on multiple nodes attached to the same link must match (you cannot change access VLAN numbers on the same physical segment).
* An access VLAN used by more than one node attached to a physical link must be defined in global **vlans** dictionary to ensure the same VLAN parameters (in particular the IPv4/IPv6 subnets) apply to all nodes using the VLAN.

(module-vlan-creating-interfaces)=
## Creating VLAN Interfaces and Routed Subinterfaces

VLAN interfaces <!-- and routed subinterfaces -->are created on-demand based on these rules:

* A VLAN interface is created for every VLAN with **mode** set to *bridge* or *irb* present on a node.
<!-- * A routed subinterface is created on every interface that has a VLAN with **mode** set to *route*.
* Routed subinterfaces are not created for access VLAN interfaces (VLAN specified in **vlan.access** attribute) when the VLAN **mode** is set to *route*.-->

The VLAN **mode** can be set in global- or node **vlans** dictionary or with the **mode** attribute of interface/link **vlan** dictionary or **trunk** dictionary within **vlan** dictionary.

The default VLAN **mode** is specified in global or node **vlan.mode** attribute.

## Physical Interface and VLAN Interface Addressing

IPv4 and/or IPv6 prefixes are automatically assigned to VLAN-enabled links:

* A VLAN is treated like a multi-access link with an IPv4/IPv6 prefix, and gets an addressing prefix assigned from the corresponding address pool if needed.
* All nodes connected to a VLAN get their IP addresses from the VLAN **prefix** (see below). Node addresses within a VLAN prefix are calculated with the algorithm used to calculate IP addresses on multi-access links.
* Whenever a VLAN access interface is attached to a link, the VLAN prefix is used to assign IP addresses to all nodes on that link.

The following rules are used to assign VLAN IPv4/IPv6 addresses to node interfaces:

* When a node is attached to a VLAN-enabled link, but does not have a **vlan** interface attribute, the VLAN IP address is assigned to physical interface.
* When the VLAN forwarding mode is set to *irb*, the node VLAN IP address is assigned to a VLAN interface.
* No IP address is assigned to the VLAN interface when the VLAN forwarding mode is set to *bridge*.
* No IP address is assigned to the physical interface that has an **access** VLAN<!--, or a VLAN **trunk**-->. <!-- You can force an IP address assignment to such an interface with **ipv4** or **ipv6** interface attribute (and become responsible for the results of your actions). -->
<!--
* When the VLAN forwarding mode is set to *route*, the VLAN IP address is  assigned to the routed subinterface (see also [](module-vlan-creating-interfaces)).
-->
