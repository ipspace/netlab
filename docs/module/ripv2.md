(module-ripv2)=
# RIPv2/RIPng Configuration Module

This configuration module configures the RIPv2 and RIPng. The module supports the following RIP features:

* IPv4 and IPv6
* Passive interfaces

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Platform Support

The following table describes per-platform support of individual RIPv2/RIPng features:

| Operating system      | IPv4<br>(RIPv2) | IPv6<br>(RIPng) | Passive<br>interfaces | Route<br>import |
| ------------------ | :-: | :-: | :-: | :-: |
| Arista EOS         | ✅  |  ❌  |  ❌  |  ❌  |
| Cisco IOSv/IOSvL2  | ✅  | ✅  | ✅ [❗](caveats-iosv) | ✅  [❗](caveats-iosv) |
| Cisco IOS XE[^18v] | ✅  | ✅  | ✅ [❗](caveats-iosv) | ✅  [❗](caveats-iosv) |
| Cumulus Linux      | ✅  | ✅  | ✅  | ✅  |
| FRR                | ✅  | ✅  | ✅  | ✅  |
| VyOS               | ✅  | ✅  | ✅  |  ❌  |

```{tip}
See [RIP Integration Tests Results](https://release.netlab.tools/_html/coverage.ripv2) for more details.
```

[^18v]: Includes Cisco CSR 1000v and Cisco Catalyst 8000v

## Lab Topology Parameters

RIPv2/RIPng module does not have global parameters. The only relevant node parameter is the **ripv2.import** parameter specifying the [import (redistribution) of routes](routing_import) into the global RIP instance (default: no route import).

RIPv2 also supports [](routing_passive) and [](routing_external).

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
