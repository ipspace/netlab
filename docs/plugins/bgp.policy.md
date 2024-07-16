(plugin-bgp-policy)=
# BGP Routing Policies Plugin

The **bgp.policy** plugin implements simple BGP routing policies :

* Per-neighbor AS-path prepending, BGP link bandwidth, BGP local preference, BGP MED, and BGP weights
* Default local preference

You can also use this plugin to apply inbound and outbound [generic routing policies](generic-routing-policies) to EBGP neighbors.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(plugin-bgp-policy-attributes)=
## Supported BGP Attributes

The plugin adds the following BGP attributes:

* **bgp.bandwidth** link attribute sets the BGP Link Bandwidth extended community. It can be an integer (in Mbps), in which case the Link Bandwidth community is attached to inbound EBGP updates[^BCP], a dictionary with **in** and **out** integer values if you want to set the Link Bandwidth community in both directions (or just on the outbound updates), or **auto** keyword if you're going to copy interface bandwidth into incoming EBGP updates[^PSV].
* **bgp.locpref** is an integer attribute that sets default local preference when applied to a node, or sets local preference on BGP updates received from an EBGP neighbor.
* **bgp.med** is an integer attribute that sets the MED attribute on BGP updates sent to an EBGP neighbor.
* **bgp.policy** is a dictionary that applies [predefined routing policies](generic-routing-policies) to inbound (**in**) or outbound (**out**) BGP updates.
* **bgp.prepend** is a dictionary configuring outbound AS-path prepending. It can contain a **count** attribute (number of times the node AS is prepended) or a **path** attribute (the prepended AS-path as a string[^ASPS])
* **bgp.weight** is an integer attribute that sets per-neighbor weight.

[^BCP]: _netlab_ configures network devices to propagate BGP Link Bandwidth extended community on IBGP sessions. The value advertised in IBGP updates is device-dependent and could be the value attached to the best path or the aggregate of EBGP values.

[^PSV]: The allowed values are platform-dependent. For example, Arista EOS and FRR can set bandwidth values in both directions but cannot add interface bandwidth. In contrast, Cisco IOS/XE can only add interface bandwidth to incoming EBGP updates.

[^ASPS]: You must quote a single AS number that you want to prepend with the **path** attribute; otherwise, the YAML parser treats it as an integer.

BGP policy attributes can be specified on a node or an interface (node-to-link attachment). The following table describes where you could apply individual attributes:

| BGP policy | Node | Interface |
|------------|:----:|:---------:|
| bandwidth  |  ❌   |    ✅     |
| locpref    |  ✅  |    ✅     |
| med        |  ❌   |    ✅     |
| policy     |  ❌   |    ✅     |
| prepend    |  ❌   |    ✅     |
| weight     |  ❌   |    ✅     |

## Platform Support

The plugin implements BGP routing policies and individual BGP policy attributes on these devices:

| Operating system    | Routing<br>policies | Local<br>preference | MED | Weight | AS-path<br>prepend | Link<br>bandwidth |
|---------------------|:----:|:----:|:----:|:----:|:-----:|:----:|
| Arista EOS          |  ✅  |  ✅  |  ✅  |  ✅  |  ✅  |  ✅  |
| Aruba AOS-CX        |  ✅  |  ✅  |  ✅  |  ✅  |  ✅  |   ❌  |
| Cisco IOSv          |  ✅  |  ✅  |  ✅  |  ✅  |  ✅  |  ✅[❗](caveats-iosv) |
| Cisco IOS-XE[^18v]  |  ✅  |  ✅  |  ✅  |  ✅  |  ✅  |  ✅[❗](caveats-iosv) |
| Cumulus Linux       |  ✅  |  ✅  |  ✅  |  ✅  |  ✅  |  ✅  |
| FRR                 |  ✅  |  ✅  |  ✅  |  ✅  |  ✅  |  ✅  |
| Nokia SR Linux      |  ✅  |  ✅  |  ✅  |  ❌  |   ❌  |   ❌  |
| Nokia SR OS         |  ✅  |  ✅  |  ✅  |  ❌  |   ❌  |  ✅  |
| VyOS                |  ✅  |  ✅  |  ✅  |  ❌  |   ✅  |   ❌  |

[^18v]: Includes Cisco CSR 1000v and Cisco Catalyst 8000v

```{tip}
See [BGP Policies Test Results](https://release.netlab.tools/_html/coverage.bgp.policy) for more details.
```

**Notes:**

* Arista EOS and Aruba CX do not support node-level default local preference. Node-level **bgp.locpref** attribute (if specified) is thus applied to all interfaces that do not have an explicit **bgp.locpref** attribute. That might interfere with the **bgp.policy** interface attributes.

## Applying Routing Policies to EBGP Neighbors

You can use **bgp.policy.in** and **bgp.policy.out** interface-level attributes to apply predefined global- or node-level [routing policies](generic-routing-policies) to EBGP sessions.  

The following lab topology contains a combination of these features:

```
defaults.device: frr
module: [ bgp, routing ]
plugin: [ bgp.policy ]

routing.policy:
  set_locpref:
    locpref: 120

nodes:
  r1:
    bgp.as: 65000
  r2:
    bgp.as: 65001
    routing.policy:
      set_med:
        med: 20

links:
- r1:
    bgp.policy.in: set_locpref
  r2:
    bgp.policy.out: set_med
```

**Notes:**
* R1 uses **set_locpref** routing policy that is not defined on R1. The global **set_locpref** routing policy is copied into R1 node data.
* R2 uses **set_med** routing policy that is defined locally.

The above lab topology results in the following FRRouting device configuration on R1[^RCP]:

[^RCP]: Only the relevant parts of the device configuration are displayed

```
router bgp 65000
 bgp router-id 10.0.0.1
 neighbor 10.1.0.2 remote-as 65001
 neighbor 10.1.0.2 description r2
 !
 address-family ipv4 unicast
  network 10.0.0.1/32
  neighbor 10.1.0.2 activate
  no neighbor 10.1.0.2 send-community extended
  neighbor 10.1.0.2 route-map set_locpref in
 exit-address-family
exit
!
route-map set_locpref permit 10
 set local-preference 120
```

## Applying Individual Policy Attributes

You could specify individual BGP policy attributes as interface-level attributes instead of defining and deploying a routing policy. This approach is probably easier to use in simple scenarios without route filters.

The plugin's device-specific configuration templates try to apply as many BGP policy attributes as possible directly to EBGP neighbor sessions. For example, **bgp.weight** is usually applied directly to a **neighbor**, as illustrated by the following FRR configuration:

```
router bgp 65000
 neighbor 10.1.0.2 remote-as 65100
 neighbor 10.1.0.2 description r1
 !
 address-family ipv4 unicast
  neighbor 10.1.0.2 activate
  neighbor 10.1.0.2 weight 10
```

Most other policy attributes have to be applied through a route map. The plugin device-specific configuration templates create per-neighbor maps using names unique to each EBGP session and apply those route maps to EBGP neighbors:

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

```{warning}
* You cannot combine **‌bgp.policy** routing policies with individual policy attributes that require a route map.
* Some devices use route maps to implement the device-wide **‌bgp.locpref** attribute. When combined with **‌bgp.policy** routing policies, these auto-generated route maps generate errors.
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

The following topology illustrates AS-path prepending functionality. On the backup link, the CE router prepends its own AS three times, and on the primary link, it prepends another AS.

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
