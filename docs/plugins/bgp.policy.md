# BGP Routing Policies Plugin

The **bgp.policy** plugin implements simple BGP routing policies :

* Per-neighbor weights, local preference and MED
* Default local preference

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Supported BGP Attributes

The plugin adds the following BGP attributes:

* **bgp.locpref** is an integer attribute that sets default local preference when applied to a node, or sets local preference on BGP updates received from an EBGP neighbor.
* **bgp.med** is an integer attribute that sets MED attribute on BGP updates sent to an EBGP neighbor.
* **bgp.prepend** is a dictionary that configures outbound AS-path prepending. It can contain a **count** attribute (number of times the node AS is prepended) or a **path** attribute (the prepended AS-path as a string[^ASPS])
* **bgp.weight** is an integer attribute that sets per-neighbor weight.

[^ASPS]: You must quote a single AS number that you want to prepend with the **path** attribute, otherwise the YAML parser treats it as an integer.

BGP policy attributes can be specified on a node or an interface (node-to-link attachment). The following table describes where you could apply individual attributes:

| BGP policy | Node | Interface |
|------------|:----:|:---------:|
| locpref    |  ✅  |    ✅     |
| med        |  ❌   |    ✅     |
| prepend    |  ❌   |    ✅     |
| weight     |  ❌   |    ✅     |

## Platform Support

The plugin implements BGP policy attributes on these devices:

| Operating system    | Local<br>preference | MED | Weight | AS-path<br>prepending |
|---------------------|:----:|:----:|:----:|:----:|
| Arista EOS          |  ✅  |  ✅  |  ✅  |  ✅  |
| Aruba AOS-CX        |  ✅  |  ✅  |  ✅  |   ✅  |
| Cisco IOSv          |  ✅  |  ✅  |  ✅  |  ✅  |
| Cisco IOS-XE        |  ✅  |  ✅  |  ✅  |  ✅  |
| Cumulus Linux       |  ✅  |  ✅  |  ✅  |  ✅  |
| FRR                 |  ✅  |  ✅  |  ✅  |  ✅  |
| Nokia SR Linux      |  ✅  |  ✅  |  ✅  |   ❌  |

**Notes:**

* Arista EOS does not support node-level default local preference. Node-level **bgp.locpref** attribute (if specified) is thus applied to all interfaces that do not have an explicit **bgp.locpref** attribute.

## Applying Policy Attributes

The plugin device-specific configuration templates try to apply as many BGP policy attributes as possible directly to EBGP neighbor sessions. For example, **bgp.weight** is usually applied directly to a **neighbor**, as illustrated by the following FRR configuration:

```
router bgp 65000
 neighbor 10.1.0.2 remote-as 65100
 neighbor 10.1.0.2 description r1
 !
 address-family ipv4 unicast
  neighbor 10.1.0.2 activate
  neighbor 10.1.0.2 weight 10
```

Most other policy attributes have to be applied through a route-map. The plugin device-specific configuration templates create per-neighbor maps using names unique to each EBGP session, and apply those route maps to EBGP neighbors:

```
router bgp 65000
 bgp default local-preference 37
 neighbor 10.1.0.2 remote-as 65100
 neighbor 10.1.0.2 description r1
 neighbor 10.1.0.6 remote-as 65100
 neighbor 10.1.0.6 description r1
 !
 address-family ipv4 unicast
  neighbor 10.1.0.2 route-map bp-r1-1-in in
  neighbor 10.1.0.2 route-map bp-r1-1-out out
  neighbor 10.1.0.6 activate
  neighbor 10.1.0.6 route-map bp-r1-2-out out
!
route-map bp-r1-1-in permit 10
 set local-preference 20
!
route-map bp-r1-1-out permit 10
 set metric 101
!
route-map bp-r1-2-out permit 10
 set metric 200
```

## Sample Topologies

The following topology illustrates a simple primary/backup scenario in which a CE-router uses weights and MED to select primary/backup uplinks.

```
---
defaults.device: frr

module: [ bgp ]
plugin: [ bgp.policy ]

nodes:
  ce:
    bgp.as: 65000
  pe:
    bgp.as: 65100

links:
- ce:
    bgp.weight: 100
    bgp.med: 50
  pe:
  name: Primary uplink
- ce:
    bgp.weight: 50
    bgp.med: 100
  pe:
  name: Backup uplink
```

The next topology illustrates AS-path prepending functionality. On the backup link, the CE-router prepends its own AS three times, on the primary link it prepends another AS.

```
---
defaults.device: frr

module: [ bgp ]
plugin: [ bgp.policy ]

nodes:
  ce:
    bgp.as: 65000
  pe:
    bgp.as: 65100

links:
- ce:
    bgp.prepend.path: "65123"
  pe:
  name: Primary uplink
- ce:
    bgp.prepend.count: 3
  pe:
  name: Backup uplink
```
