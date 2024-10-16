(module-ripv2)=
# RIPv2/RIPng Configuration Module

This configuration module configures the RIPv2 and RIPng. The module supports the following RIP features:

* IPv4 and IPv6
* Passive interfaces
* VRF RIPv2/RIPng instances

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Platform Support

The following table describes per-platform support of individual RIPv2/RIPng features:

| Operating system      | IPv4<br>(RIPv2) | IPv6<br>(RIPng) | Passive<br>interfaces | Route<br>import | VRF<br>instances | RIP<br>timers |
| ------------------ | :-: | :-: | :-: | :-: | :-: | :-: |
| Arista EOS         | ✅  |  ❌  |  ❌  |  ❌  |  ❌  | ✅ |
| Cisco IOSv/IOSvL2  | ✅  | ✅  | ✅ [❗](caveats-iosv) | ✅  [❗](caveats-iosv) | ✅ | ✅ |
| Cisco IOS XE[^18v] | ✅  | ✅  | ✅ [❗](caveats-iosv) | ✅  [❗](caveats-iosv) | ✅ | ✅ |
| Cumulus Linux      | ✅  | ✅  | ✅  | ✅  | ✅  | ✅ |
| FRR                | ✅  | ✅  | ✅  | ✅  | ✅  | ✅ |
| VyOS               | ✅  | ✅  | ✅  |  ❌  |

```{tip}
See [RIP Integration Tests Results](https://release.netlab.tools/_html/coverage.ripv2) for more details.
```

[^18v]: Includes Cisco CSR 1000v, Cisco Catalyst 8000v, Cisco IOS-on-Linux (IOL), and IOL Layer-2 image.

(rip-params)=
## Lab Topology Parameters

You can change the RIPv2/RIPng timers with the global **rip.timers** dictionary ([more details](rip-timers)).

The RIPv2/RIPng configuration module supports these node parameters:

* **rip.timers**: Change RIP timers for a single node
* **ripv2.import**: Specify the [import (redistribution) of routes](routing_import) into the global RIP instance (default: no route import).

RIPv2 also supports [](routing_passive) and [](routing_external).

(rip-vrf)=
## VRF Parameters

* By default, _netlab_ redistributes BGP- and connected routes into VRF RIPv2/RIPng instances on all network devices. You can change that on devices supporting configurable route import with the **[ripv2.import](routing_import)** VRF parameter.
* Use **rip.timers** VRF parameter to change RIP timers for a single VRF instance
* Set **ripv2.active** to *True* to force a VRF to use RIPv2/RIPng even when no routers are attached to the VRF interfaces.
* To disable RIPv2/RIPng in a VRF set **ripv2** to *False* (see also [](routing_disable_vrf)).

(rip-timers)=
## Changing RIP Timers

You can change the RIP protocol timers with the **rip.timers** global/node/VRF dictionary. The dictionary has these elements:

* **update**: periodic RIP update timer. Default: 30 seconds, minimum: 5 seconds
* **timeout**: route expiration timer. Default: six times the **update** timer, minimum: 5 seconds)
* **garbage**: garbage collection timer (the time after which an invalid route is removed from the routing table). Default: four times the **update** timer, minimum: 5 seconds

## Example

We want to create a simple two-router RIPv2 network using Cumulus Linux:

```
defaults.device: cumulus
module: [ ripv2 ]
```

The lab has two nodes and a link between them:
```
nodes: [ r1, r2 ]
links: [ r1-r2 ]
```

This is the resulting RIPv2 FRRouting configuration for R1:

```
router rip
 network lo
 network swp1
 version 2
```
