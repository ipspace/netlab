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

| Operating system      | IPv4<br>(RIPv2) | IPv6<br>(RIPng) | Passive<br>interfaces | Route<br>import | VRF<br>instances |
| ------------------ | :-: | :-: | :-: | :-: | :-: |
| Arista EOS         | ✅  |  ❌  |  ❌  |  ❌  |
| Cisco IOSv/IOSvL2  | ✅  | ✅  | ✅ [❗](caveats-iosv) | ✅  [❗](caveats-iosv) |
| Cisco IOS XE[^18v] | ✅  | ✅  | ✅ [❗](caveats-iosv) | ✅  [❗](caveats-iosv) |
| Cumulus Linux      | ✅  | ✅  | ✅  | ✅  | ✅  |
| FRR                | ✅  | ✅  | ✅  | ✅  | ✅  |
| VyOS               | ✅  | ✅  | ✅  |  ❌  |

```{tip}
See [RIP Integration Tests Results](https://release.netlab.tools/_html/coverage.ripv2) for more details.
```

[^18v]: Includes Cisco CSR 1000v and Cisco Catalyst 8000v

## Lab Topology Parameters

RIPv2/RIPng module does not have global parameters. The only relevant node parameter is the **ripv2.import** parameter specifying the [import (redistribution) of routes](routing_import) into the global RIP instance (default: no route import).

RIPv2 also supports [](routing_passive) and [](routing_external).

## VRF Parameters

* By default, _netlab_ redistributes BGP- and connected routes into VRF RIPv2/RIPng instances on all network devices. You can change that on devices supporting configurable route import with the **[ripv2.import](routing_import)** VRF parameter.
* Set **ripv2.active** to *True* to force a VRF to use RIPv2/RIPng even when no routers are attached to the VRF interfaces.
* To disable RIPv2/RIPng in a VRF set **ripv2** to *False* (see also [](routing_disable_vrf)).

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
