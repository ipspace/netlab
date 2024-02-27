# Attributes on VLAN Access Interfaces

_netlab_ supports _routed_ VLANs -- VLAN subinterfaces of physical interfaces -- and _bridged_[^BSW] VLANs -- VLAN interfaces grouped under a virtual VLAN interface ([more details](vlan-forwarding-modes)).

[^BSW]: What marketers would call _switched_ ;)

## Attributes on Routed VLAN Access Links

It makes sense to define most _netlab_ link- or interface attributes on a VLAN access link that belongs to a routed VLAN. After all, each such link is transformed into a separated routed interface and can use all layer-3 attributes. For example, it's perfectly fine to define a different OSPF cost for every link in a routed VLAN:

```
vlans:
  red:
    mode: route
    links:
    - r1:
      c1:
      ospf.cost: 10
    - r1:
      c2:
      ospf.cost: 20
```

## Attributes on Bridged/IRB VLAN Access Links

Defining layer-3 attributes (or even some layer-2 attributes like MTU or bandwidth) on a VLAN access interface that is a child of a VLAN interface makes no sense. For example, it's impossible to have different OSPF costs on links that are bridged together under a single VLAN interface:

```
vlans:
  red:
    mode: route
    links:
    - r1:
      c1:
      ospf.cost: 10
    - r1:
      c2:
      ospf.cost: 20
```

_netlab_ silently ignores link- and interface attributes on bridged (OK, switched) VLAN access or trunk interfaces[^TAC] and removes them from the transformed data model to ensure they would not be configured on the physical interface[^IBRF].

[^TAC]: VLAN trunk interfaces are just a bundle of VLAN access interfaces belonging to the same physical port.

[^IBRF]: Routers and switches cannot use layer-3 parameters defined on access interfaces of bridge VLANs anyway. They would either silently ignore them or report configuration errors.

For example, the above lab topology results in the following interfaces on R1. OSPF cost is not specified on the VLAN access links or on the VLAN interface -- interface parameters are not copied from VLAN access interfaces to the virtual VLAN interface[^ADMC].

[^ADMC]: Actual interface data might change as future _netlab_ releases add new attributes.

```
- bridge: X_1
  ifindex: 1
  ifname: Ethernet1
  linkindex: 1
  type: lan
  vlan:
    access: red
    access_id: 1000
- bridge: X_2
  ifindex: 2
  ifname: Ethernet2
  linkindex: 2
  type: lan
  vlan:
    access: red
    access_id: 1000
- bridge_group: 1
  ifindex: 3
  ifname: Vlan1000
  ipv4: 172.16.0.1/24
  name: VLAN red (1000) -> [c1,c2]
  neighbors:
  - ifname: eth1
    ipv4: 172.16.0.2/24
    node: c1
  - ifname: eth1
    ipv4: 172.16.0.3/24
    node: c2
  ospf:
    area: 0.0.0.0
    passive: true
  role: stub
  type: svi
  virtual_interface: true
  vlan:
    mode: irb
```

## Using Physical Interface Attributes on VLAN Access Links

You might need to retain the physical interface attributes (for example, _link aggregation group_) on VLAN access interfaces.

```{tip}
Use this functionality only for attributes that define device behavior _below the IEEE 802.1 bridge_, for example, link aggregation groups or physical interface attributes like link speed or breakout cables.
```

The following topology defines a new `lag` link attribute[^CT] and uses it on two VLAN access links to make them part of the same link group:

```
defaults.attributes.link.lag:

vlans:
  red:
    links:
    - r1:
      r2:
      lag: 1
    - r1:
      r2:
      lag: 1
```

[^CT]: This document describes a potential implementation of link aggregation groups in the lab topology. You must use the new attribute in custom configuration templates to configure LAG on your devices.

The default processing of VLAN access interfaces removes the `lag` attribute from the physical interfaces. To retain that attribute, you have to tell the VLAN module it's a *physical interface attribute* -- you have to add it to the **phy_ifattr** VLAN attributes using the line in the lab topology (or [user defaults](defaults-user-file)):

```
defaults.vlan.attributes.phy_ifattr.lag: True
```

After that change, the physical interfaces retain the `lag` attribute, and it's not copied to the VLAN virtual interface. The following printout contains transformed interface data for R1[^ADMC]:

```
- bridge: X_1
  ifindex: 1
  ifname: Ethernet1
  lag: 1
  linkindex: 1
  type: lan
  vlan:
    access: red
    access_id: 1000
- bridge: X_2
  ifindex: 2
  ifname: Ethernet2
  lag: 1
  linkindex: 2
  type: lan
  vlan:
    access: red
    access_id: 1000
- bridge_group: 1
  ifindex: 3
  ifname: Vlan1000
  ipv4: 172.16.0.1/24
  name: VLAN red (1000) -> [r2]
  neighbors:
  - ifname: Vlan1000
    ipv4: 172.16.0.2/24
    node: r2
  ospf:
    area: 0.0.0.0
    network_type: point-to-point
    passive: false
  type: svi
  virtual_interface: true
  vlan:
    mode: irb
```
