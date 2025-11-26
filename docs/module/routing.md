(generic-routing)=
# Generic Routing Configuration Module

This configuration module implements generic routing features:

* [Routing policies (route maps)](generic-routing-policies)
* [Prefix filters (prefix-lists)](generic-routing-prefixes)
* [BGP AS-path filters](generic-routing-aspath)
* [BGP community filters](generic-routing-community)
* [Static routes](generic-routing-static)

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(generic-routing-platforms)=
## Platform Support

The following table describes high-level per-platform support of generic routing features:

| Operating system      | Routing<br>policies | Prefix<br>filters| AS-path<br>filters | BGP<br>communities | Static<br>routes|
| ------------------ |:--:|:--:|:--:|:--:|:--:|
| Arista EOS         | ✅ | ✅ | ✅ | ✅ | ✅ |
| Aruba AOS-CX       | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cisco IOS/XE[^18v] | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cisco IOS/XR[^XR]  | ❌  | ❌  | ❌  | ❌  | ✅ |
| Cumulus Linux      | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cumulus NVUE 5.x   | ❌  | ❌  | ❌  | ❌  | ✅ |
| Dell OS10          | ✅ | ✅ | ✅ | ✅ | ✅ |
| FRR                | ✅ | ✅ | ✅ | ✅ | ✅ |
| Linux              | ❌  | ❌  | ❌  | ❌  | ✅ |
| Junos              | ✅ | ✅ | ✅ | ✅ | ✅ |
| Nokia SR Linux     |  ✅ | ✅ [❗](caveats-srlinux) | ❌  | ❌  | ❌  |
| Nokia SR OS[^SROS] | ✅ | ❌  | ❌  | ❌  | ❌ |
| OpenBSD            | ❌  | ❌  | ❌  | ❌  | ✅ |
| VyOS               | ✅ | ✅ | ✅ | ✅ | ❌ |

```{tip}
See [Routing Integration Tests Results](https://release.netlab.tools/_html/coverage.routing) for more details.
```

[^18v]: Includes Cisco IOSv, Cisco IOSvL2, Cisco CSR 1000v, Cisco Catalyst 8000v, Cisco IOS-on-Linux (IOL), and IOL Layer-2 image.

[^SROS]: Includes the Nokia SR-SIM container and the Virtualized 7750 SR and 7950 XRS Simulator (vSIM) virtual machine

[^XR]: Includes IOS XRv, IOS XRd, and Cisco 8000v

```{include} routing-policy.txt
```
```{include} routing-prefix.txt
```
```{include} routing-aspath.txt
```
```{include} routing-clist.txt
```
```{include} routing-static.txt
```
```{include} routing-advanced.txt
```
