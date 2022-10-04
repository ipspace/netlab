# VLANs

The VLAN configuration module implements VLANs and VLAN-related interfaces including:

* Access VLANs
* VLAN trunks, including configurable native VLAN
* VLAN interfaces (integrated routing and bridging)
* Bridging-only and IRB VLANs
* Routed subinterfaces

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
| Arista EOS            | ✅  | ✅  | ✅  | ✅ | ✅ |
| Cisco IOSv            | ✅  | ✅  | ✅  | ✅ | ✅ |
| Cisco Nexus OS        | ✅  | ✅  | ✅  | ✅ | ✅ |
| Cumulus Linux         | ✅  | ✅  | ✅  | ✅ | ✅ |
| Dell OS10             | ✅  | ✅  | ❌   | ✅ | ✅ |
| FRR [❗](../caveats.html#caveats-frr-config) | ✅  | ✅  | ✅  | ✅ | ✅ |
| Mikrotik RouterOS 6   | ✅  | ✅  | ✅  | ✅ | ✅ |
| Mikrotik RouterOS 7   | ✅  | ✅  | ✅  | ✅ | ✅ |
| Nokia SR Linux        | ✅  | ✅  | ✅   | ✅ | ✅ |
| Nokia SR OS           | ✅  | ✅  | ✅   | ✅ | ✅ |
| VyOS                  | ✅  | ✅  | ✅   | ✅ | ✅ |

## VLAN Connectivity Model

The VLAN configuration module assumes you're creating a sane design in which:

* VLAN numbers are globally unique (you're not reusing 802.1q values)
* Every VLAN is contiguous and might span multiple physical links (please note that VLANs bridged across VXLAN or MPLS are still contiguous)
* Every VLAN uses a unique IP subnet across all physical links where it's used.
* On access links, all VLAN-capable devices connected to a link use the same access VLAN.
* On trunk links, all VLAN-capable devices using native VLAN use the same native VLAN.

It might be possible to build topologies that deviate from these rules, but don't be surprised when the results look weird.

## Deployment Recommendations

The VLAN module tries to support many different platform-specific VLAN configuration paradigms, and the resulting maze of various bits and pieces might frustrate the unwary. Following these guidelines might help you avoid the frustration:

* Use **route** VLANs only in a router-on-a-stick or multi-hop VRF Lite designs.
* While it's possible to mix **route** and **irb** VLANs on the same device, the results are not always intuitive. Don't do that -- a device should be a pure router (terminating **route** VLANs) or a layer-3 switch (forwarding within and between **bridge** or **irb** VLANs) but not both.
* Do not use **mode: route** on access VLANs. Use native IP connectivity.
* Avoid **mode: route** on native VLANs. Some devices might not like that approach.
* Don't use link attributes to modify VLANs in a VLAN trunk. Use VLAN attributes.
* Never combine multiple [forwarding modes](vlan-forwarding-modes) of a single VLAN *within a single node*. Using **route** VLAN mode on a router-on-a-stick and **bridge**/**irb** VLAN mode on attached switch is perfectly fine.
* You [REALLY SHOULD NOT](https://www.rfc-editor.org/rfc/rfc6919#section-3) use VLANs on links [connecting a node back to itself](../example/link-definition.md#crazy-scenarios)[^BAD1]. [Routed VLANs](vlan-addressing-routed) might work[^NF], any other VLAN setup on such a link will result in a miserable failure.

[^BAD1]: One of the really bad ideas we had in the past.

[^NF]: But don't expect us to fix bugs you might stumble upon. You've been warned ;)

## Module Parameters

The following default parameters are used to when assigning VLAN IDs:

* **vlan.start_vlan_id**: Specifies the first auto-assigned VLAN ID (default: 1000).

To change these defaults, set **defaults.vlan._value_** parameter(s) in lab topology.

(module-vlan-definition)=
## VLAN Definition

VLANs are defined in a global- or node-specific **vlans** dictionary, allowing you to create network-wide VLANs or local VLANs.

Global- and node VLAN parameters are merged to get final VLAN data for individual nodes, allowing you to override global VLAN parameters on individual nodes.

```{warning}
Use unique VLAN names when defining node-specific VLANs. There's a subtle interaction between global- and node-specific VLAN definitions.
```

The keys of the **vlans** dictionary are VLAN names, the values are VLAN definitions. A VLAN definition could be empty or a dictionary with one or more of these attributes:

* **id** -- 802.1q VLAN tag
* **vni** -- VXLAN VNI (managed by [VXLAN configuration module](vxlan.md))
* **vrf** -- the VRF VLAN belongs to
* **mode** -- default VLAN forwarding mode: **route**, **bridge** or **irb**.
* **prefix** -- IP prefix assigned to the VLAN. The value of the prefix could be an IPv4 prefix or a dictionary with **ipv4** and **ipv6** keys.
* **pool** -- addressing pool used to assign IPv4/IPv6 prefixes to the VLAN. VLAN prefixes are allocated from addressing pools before interface address assignments.
* A VLAN definition can also contain other valid link- or interface-level parameters (including link **role**, addressing **pool**, VRF name, OSPF cost...).

VLAN definitions lacking **id** attribute get [default VLAN ID](default-vlan-values) assigned during the topology transformation process.

(default-vlan-values)=
### Default VLAN Values

VLAN definitions without **id** attribute will get a VLAN ID assigned automatically. The first auto-assigned VLAN ID is specified in the **vlan.start_id** global attribute; ID assignment process skips IDs assigned to existing VLANs.

(vlan-forwarding-modes)=
### VLAN Forwarding Modes

VLANs with **mode** set to **bridge** or **irb** are configured as VLAN/SVI interfaces or bridge groups (BVI interfaces or Linux bridge) -- VLAN access or trunk interfaces using the same VLAN are bridged.

VLANs with **mode** set to **route** are configured as routed subinterfaces under the VLAN trunk interface. Use this mode primarily for designs using VLAN trunks to implement router-on-a-stick or [multi-hop VRF](https://github.com/ipspace/netlab-examples/tree/master/VRF/multihop-vrf-lite). Access VLAN interfaces with **mode** set to **route** are identical to non-VLAN interfaces.

You can set VLAN forwarding mode within individual links or interfaces with **vlan.mode** attribute, within a node or global **vlans** definition, or with **vlan.mode** node- or global parameter.

The precedence of various **vlan.mode** parameters (from highest to lowest) is as follows:

* Interface **vlan.mode**, potentially inherited from parent interface **vlan.mode** or from parent interface **vlan.trunk** dictionary.
* Link **vlan.mode**, potentially inherited from parent link **vlan.trunk** dictionary
* **mode** set in node **vlans** definition
* Node **vlan.mode** setting[^NVM]
* **mode** set in global **vlans** definition
* Global **vlan.mode** setting

The default forwarding mode is **irb**.

[^NVM]: Node setting takes precedence over global VLAN setting to allow you to attach a router to a VLAN trunk without setting too many parameters.

(module-vlan-interface)=
## Using VLANs on Interfaces and Links

To use a VLAN on a link, add **vlan** dictionary to a link or an interface on a link. The VLAN dictionary may contain the following attributes:

* **access** -- the name of access VLAN configured on the link or interface
* **trunk** -- a list or dictionary of VLANs configured on a trunk port -- see [](module-vlan-trunk-attributes) for more details.
* **native** -- the name of native VLAN configured on a trunk port
* **mode** -- the default VLAN forwarding mode (route/bridge/irb) for this link or interface -- overrides the node- or global forwarding mode

### Access VLAN Restrictions

To keep the VLAN complexity manageable, the VLAN configuration module enforces these rules:

* Access VLAN defined with link **vlan.access** attribute applies to every attached node that uses **vlan** configuration module.
* Access VLANs defined with interface **vlan.access** attribute on multiple nodes attached to the same link must match (you cannot change access VLAN numbers on the same physical segment).
* An access VLAN used by more than one node attached to a physical link must be defined in global **vlans** dictionary to ensure the same VLAN parameters (in particular the IPv4/IPv6 subnets) apply to all nodes using the VLAN.

### Trunk VLAN Restrictions

VLAN configuration module enforces these rules:

* VLANs listed within a **vlan.trunk** attribute must be defined as global VLANs.
* Native VLAN specified in **vlan.native** must be included in **vlan.trunk** list.
* Native VLAN must match across all VLAN-capable nodes connected to a link.

(module-vlan-creating-interfaces)=
## Creating VLAN Interfaces and Routed Subinterfaces

VLAN interfaces and subinterfaces are created on-demand based on these rules:

* A VLAN/SVI/BVI interface is created for every VLAN with **mode** set to *bridge* or *irb* present on a node.
* VLAN subinterfaces are created on VLAN trunks on platforms behaving more like routers than switches (example: Cisco IOS).
* A routed VLAN subinterface is created on every interface that has a VLAN with **mode** set to *route*.
* Routed VLAN subinterfaces are not created for access VLAN interfaces (VLAN specified in **vlan.access** attribute) when the VLAN **mode** is set to *route*. There is no difference between routed access VLAN interface and an interface without VLAN configuration.

The VLAN **mode** can be set in global- or node **vlans** dictionary or with the **vlan.mode** interface/link attribute.

### VLAN Interface Parameters

You can change VLAN interface[^VLANIF] parameters within the node **vlans** dictionary. For example, use the following definitions to set the OSPF cost for the **red** VLAN interface on node **s1**:

[^VLANIF]: VLAN/SVI/BVI interfaces or router VLAN subinterfaces

```
vlans:
  red:

nodes:
  s1:
    module: [ ospf,vlan ]
    vlans:
      red:
        ospf.cost: 10

links:
- s1:
    vlan.access: red
  ...
```

You can also set interface parameters for every interface connected to a VLAN within global VLAN definition. For example, you could set the OSPF cost for all interfaces connected to the **red** VLAN:

```
vlans:
  red:
    ospf.cost: 10

nodes:
  s1:
    module: [ ospf,vlan ]

links:
- s1:
    vlan.access: red
  ...
```

Finally, you can set the parameters of an individual routed VLAN subinterface within the **vlan.trunk** link- or interface- dictionary.

```{warning}
Don't try to set VLAN interface parameters on access or trunk links; you might get unexpected results.
```

(module-vlan-trunk-attributes)=
### Modifying Attributes of VLANs in a VLAN Trunk

Use a list of VLANs in a **vlan.trunk** attribute when you don't want to change individual VLAN attributes on a link/interface level. Use a **vlan.trunk** dictionary when you want to set additional parameters for the virtual links created for individual VLAN in the trunk.

You could use this functionality to set VLAN forwarding mode (**vlan.mode**) on individual VLANs in a trunk[^NMT], or to set parameters for a routed VLAN subinterface.

```{warning}
Use interface- or link attributes within the **‌trunk** dictionary only on routed VLAN subinterfaces. Attributes for VLAN/SVI interfaces should be set within global or node-level **‌vlans** definition.
```

For example, to set OSPF cost for a routed subinterface for VLAN *red* without changing the OSPF cost for *blue* or *green* VLAN, use this link definition:

```
links:
- r1:
    vlan.trunk:
      red:
        vlan.mode: route
        ospf.cost: 10
  s1:
  vlan.trunk: [ red, green, blue ]
```

[^NMT]: Some platforms do not support a mix of bridged and routed VLANs on a single physical interface.

(vlan-addressing)=
### VLAN Addressing

IPv4 and/or IPv6 prefixes are automatically assigned to VLAN-enabled links. A VLAN trunk is decomposed into a number of virtual links (one per VLAN); the VLAN addressing rules are then applied to those virtual links.

A VLAN is treated like a multi-access link with an IPv4/IPv6 prefix. It can have a static prefix specified with the **prefix** VLAN attribute, or get a prefix allocated from the address pool specified with the **pool** VLAN attribute (default: **lan** pool).

When at least one node attached to a VLAN-enabled link uses VLAN forwarding mode **irb** or **bridge** for that VLAN, all parts of that VLAN get the VLAN-wide prefix:

* VLAN **prefix** is copied into the link (or virtual link) **prefix**.
* All nodes connected to a VLAN get their IP addresses from the VLAN **prefix**. Node addresses within a VLAN prefix are calculated with the algorithm used to calculate IP addresses on multi-access links.
* Whenever a VLAN access interface is attached to a link, the VLAN prefix is used to assign IP addresses to all nodes on that link.

(vlan-addressing-routed)=
The above rule does not apply to *routed* access interfaces or virtual links. A *routed* VLAN link is a link on which all connected nodes that use **vlan** configuration module use forwarding mode **route** for that VLAN.

A unique prefix is assigned to every *routed* VLAN link (access interface or trunk link VLAN member). The prefix cannot be specified with the VLAN **prefix** attribute; use **pool** VLAN attribute to specify the address pool to be used for the virtual link. You can also specify the link prefix in the **prefix** attribute of an [individual VLAN trunk member](module-vlan-trunk-attributes).

```{note}
If you want to use unnumbered VLAN member links, set VLAN **pool** to **unnumbered**.
```

### Physical Interface and VLAN Interface Addressing

The following rules are used to assign VLAN IPv4/IPv6 addresses to node interfaces:

* When a node is attached to a VLAN-enabled link, but does not have a **vlan** interface attribute, the VLAN IP address is assigned to physical interface.
* When the VLAN forwarding mode is set to *irb*, the node VLAN IP address is assigned to a VLAN interface.
* When the VLAN forwarding mode of a VLAN in a VLAN trunk is set to *route*, the node VLAN IP address is  assigned to the routed subinterface (see also [](module-vlan-creating-interfaces)).
* No IP address is assigned to the VLAN interface when the VLAN forwarding mode is set to *bridge*.
* No IP address is assigned to the physical interface that has an **access** or **native** VLAN with **mode** set to *bridge* or *irb*. You can try to force an IP address assignment to such an interface with **ipv4** or **ipv6** interface attribute and become responsible for the results of your actions.
* Interfaces with **access** or **native** VLAN that has **mode** set to *route* are treated like regular interfaces and get IP addresses. These interfaces will be configured as regular layer-3 interfaces without *access* or *native* VLAN[^PLER].
* IP prefixes are not assigned to the physical interfaces with VLAN trunks. If you want to assign IP addresses to default native VLAN (1), use **pool** or **prefix** link attribute.

[^PLER]: There is no difference between a regular layer-3 interface and an access VLAN interface that does no bridging and only routes IP packets. The proof is left as an exercise for the reader.
 
(module-vlan-caveats)=
## Known Caveats

If we document them, they're not bugs, right?

* Devices connected to a single-node VLAN will not have VLAN-wide list of neighbors on the interface connected to that node. EBGP sessions that should be configured over that VLAN might be missing.

