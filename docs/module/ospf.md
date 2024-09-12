(module-ospf)=
# OSPF Configuration Module

This configuration module configures OSPFv2 and OSPFv3 routing processes on most supported platforms (see [supported features](#supported-features) and [platform support](#platform-support)).

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

```{note}
Use **[netlab report](../netlab/report.md)** or **[netlab create -o report](../netlab/create.md)** commands to create reports on OSPF areas, routers, and interfaces. Use **[‌netlab show reports ospf](netlab-show-reports)** command to display available OSPF reports.
```

## Supported Features

Supported OSPF features:

* OSPFv2 and/or OSPFv3 (see platform support table and [address families](routing_af))
* Multi-area deployment
* Per-link cost and asymmetric costs
* OSPF network type
* Reference bandwidth
* Unnumbered point-to-point interfaces
* [Passive interfaces](routing_passive)
* [Static router ID](routing_router_id)
* [Route import](routing_import) (redistribution)
* [Default route origination](ospf-default)
* BFD (optionally with RFC9355 strict mode)
* VRF OSPFv2 instances (on platforms with [VRF support](module-vrf-platform-support))

Missing features:

* Stub and NSSA areas
* Virtual links
* Opaque LSA
* Multi-area adjacencies
* Demand circuits
* A gazillion nerd knobs and IETF quirks

Need one of those? Create a plugin and contribute it.

(ospf-platform)=
## Platform Support

The following table describes per-platform support of individual router-level OSPF features:

| Operating system         | Areas | Reference<br/>bandwidth | OSPFv3 | Route<br>import | Default<br>route |
| ------------------------ |:-:|:-:|:-:|:-:|:-:|
| Arista EOS               | ✅| ✅| ✅| ✅| ✅|
| Aruba AOS-CX             | ✅| ✅| ✅| ✅| ✅|
| Cisco IOSv/IOSvL2        | ✅| ✅| ✅| ✅| ✅|
| Cisco IOS XRv            | ✅| ✅| ✅| ❌ | ❌ |
| Cisco IOS XE[^18v]       | ✅| ✅| ✅| ✅| ✅|
| Cisco Nexus OS           | ✅| ✅| ✅| ❌ | ❌ |
| Cumulus Linux            | ✅| ✅| ✅| ✅| ✅|
| Cumulus Linux 5.0 (NVUE) | ✅| ✅| ❌ | ❌ | ❌ |
| Dell OS10 ([❗](caveats-os10)) | | ✅| ✅| ✅| ❌ | ❌ |
| Fortinet FortiOS         |[❗](caveats-fortios)| ✅ | ❌ | ❌ | ❌ |
| FRR                      | ✅| ✅| ✅| ✅| ✅|
| Junos[^Junos]            | ✅| ✅| ✅| ❌ | ❌ |
| Mikrotik RouterOS 6      | ✅| ❌ | ❌ | ❌ | ❌ |
| Mikrotik RouterOS 7      | ✅| ❌ | ✅| ❌ | ❌ |
| Nokia SR Linux           | ✅| ✅| ✅| ✅ [❗](caveats-srlinux) | ✅ [❗](caveats-srlinux) |
| Nokia SR OS              | ✅| ✅| ✅| ❌ | ❌ |
| VyOS                     | ✅| ✅| ✅| ✅| ✅|

**Notes:**
* Dell OS10 does not support OSPF on the so-called *Virtual Network* interface, the VLAN implementation model currently used in our templates.

[^18v]: Includes Cisco CSR 1000v and Cisco Catalyst 8000v

[^Junos]: Includes vMX, vSRX, vPTX and vJunos-switch

The following devices support BFD with OSPF:

| Operating system         | BFD  | BFD<br/>Strict-Mode |
| ------------------------ | :--: | :--: |
| Arista EOS               |  ✅  |  ❌   |
| Aruba AOS-CX             |  ✅  |  ❌   |
| Cisco IOS                |  ✅  |  ❌   |
| Cisco IOS XE[^18v]       |  ✅  |  ❌   |
| Cisco Nexus OS           |  ✅  |  ❌   |
| Cumulus Linux            |  ✅  |  ❌   |
| Dell OS10                |  ✅  |  ❌   |
| Junos[^Junos]            |  ✅  |  ❌   |
| Mikrotik RouterOS 6      |  ✅  |  ❌   |
| Nokia SR Linux           |  ✅  |  ❌   |
| Nokia SR OS              |  ✅  |  ✅  |
| VyOS                     |  ✅  |  ❌   |

**Notes:**
* Mikrotik RouterOS and VyOS support BFD on OSPF only with the system default values for interval and multiplier.

```{tip}
See [OSPFv2](https://release.netlab.tools/_html/coverage.ospf.ospfv2) and [OSPFv3](https://release.netlab.tools/_html/coverage.ospf.ospfv3) Integration Tests Results for more details.
```

OSPF is also supported on these [routing daemons](platform-daemons):

| Operating system         | Areas | Reference<br/>bandwidth | OSPFv3 | BFD  | BFD<br/>Strict-Mode |
| ------------------------ |:--:|:--:|:--:|:--:|:--:|
| BIRD                     | ✅ | ❌  | ✅ | ❌  | ❌  |

(ospf-interface)=
The following table documents the interface-level OSPF features:

| Operating system         | Cost  | Network<br />type | Unnumbered<br />IPv4 interfaces | Passive<br />interfaces |
| ------------------------ |:--:|:--:|:--:|:--:|
| Arista EOS               | ✅ | ✅ | ✅ | ✅ |
| Aruba AOS-CX             | ✅ | ✅ | ❌  | ✅ |
| Cisco IOS                | ✅ | ✅ | ❌  | ✅ |
| Cisco IOS XE             | ✅ | ✅ | ✅ | ✅ |
| Cisco IOS XRv            | ✅ | ✅ | ✅ | ✅ |
| Cisco Nexus OS           | ✅ | ✅ | ✅ | ✅ |
| Cumulus Linux            | ✅ | ✅ | ✅ | ✅ |
| Cumulus Linux 5.0 (NVUE) | ✅ | ✅ | ✅ | ✅ |
| Dell OS10                | ✅ | ✅ | ❌  | ✅ |
| Fortinet FortiOS         | ✅ | [❗](caveats-fortios) | ❌ | ✅ |
| FRR                      | ✅ | ✅ | ✅ | ✅ |
| Junos[^Junos]            | ✅ | ✅ | ✅ | ✅ |
| Mikrotik RouterOS 6      | ✅ | ✅ | ❌  | ✅ |
| Mikrotik RouterOS 7      | ✅ | ✅ | ❌  | ✅ |
| Nokia SR Linux           | ✅ | ✅ | ✅ | ✅ |
| Nokia SR OS              | ✅ | ✅ | ✅ | ✅ |
| VyOS                     | ✅ | ✅ | ✅ | ✅ |

**Notes:**
* Arista EOS, Cisco Nexus OS, SR Linux, and Dell OS10 support point-to-point and broadcast network types. Other network types will not be configured.
* SR OS supports point-to-point, broadcast, and non-broadcast network types. It will not configure a point-to-multipoint network type.

OSPF routing daemons support these interface-level features:

| Operating system         | Cost  | Network<br />type | Unnumbered<br />IPv4 interfaces | Passive<br />interfaces |
| ------------------------ |:--:|:--:|:--:|:--:|
| BIRD                     | ✅ | ✅ | ❌  | ✅ |

**Notes:**
* Routing daemons usually have a single interface. Running OSPF on them seems frivolous unless you need OSPF to get paths toward remote endpoints of IBGP sessions.

## Global Parameters

* **ospf.reference_bandwidth** sets the OSPF auto-cost reference bandwidth (in Mbps) for all devices in the network.
* **ospf.bfd.strict** enables RFC9355 BFD Strict-Mode (default: False)

## Node Parameters

* **ospf.process** -- process ID (default: 1)
* **ospf.af** -- [OSPF address families](routing_af), usually set by the data transformation code. Configures OSPFv2 when **ospf.af.ipv4** is set to `True` and OSPFv3 (on devices that support OSPFv3) when **ospf.af.ipv6** is set to `True`. 
* **ospf.area** -- default OSPF area (default: 0.0.0.0). Used on links without explicit OSPF area and the loopback interface.
* **ospf.default** -- External default route origination ([more details](ospf-default))
* **ospf.reference_bandwidth** -- per-node OSPF auto-cost reference bandwidth (in Mbps).
* **ospf.bfd** -- enable BFD for OSPF (default: False)
* **ospf.import** -- [import (redistribute) routes](routing_import) into the global OSPF instance. By default, no routes are redistributed into the global OSPF instance.
* **ospf.router_id** -- set [static router ID](routing_router_id).

You can specify most node parameters as global values (top-level topology elements) or within individual nodes (see [example](#example) for details).

## VRF Parameters

* You can specify the default area for a VRF OSPF instance with VRF-level **ospf.area** parameter
* By default, _netlab_ redistributes BGP- and connected routes into VRF OSPF instances on all network devices. You can change that on devices supporting configurable route import with the **[ospf.import](routing_import)** VRF parameter.
* You can change the [router ID](routing_router_id) of a VRF OSPF instance with **ospf.router_id** parameter. Use this parameter when building back-to-back links between VRFs on the same node.
* Set **ospf.active** to *True* to force a VRF to use OSPF even when no routers are attached to the VRF interfaces.
* To disable OSPF in a VRF set **ospf** to *False* (see also [](routing_disable_vrf)).
* To originate a default route in a VRF OSPF instance, set the **ospf.default** VRF parameter ([more details](ospf-default))

## Link Parameters

* **ospf.cost** -- OSPF cost
* **ospf.area** -- OSPF area. Use on ABRs; node-level OSPF area is recommended for intra-area routers.
* **ospf.network_type** -- Set OSPF network type. Allowed values are **point-to-point**, **point-to-multipoint**, **broadcast** and **non-broadcast**[^NS]. See also [Default Link Parameters](#default-link-parameters)
* **ospf.bfd** -- turn BFD for OSPF on or off on an individual link or interface (boolean value, overrides node **ospf.bfd** setting)
* **ospf.passive** -- explicitly enable or disable [passive interfaces](routing_passive)

[^NS]: Some OSPF network types (non-broadcast or point-to-multipoint) are not supported by all platforms.

**Note:** The same parameters can be specified for individual link nodes.

OSPF is automatically started on all interfaces within an autonomous system (interfaces with no EBGP neighbors; see also [](routing_external)). To disable OSPF on an intra-AS link, set **ospf** to *False* (see also [](routing_disable)).

```{tip}
* Management interfaces are never added to the OSPF process. They are not in the set of device links and, thus, not considered in the OSPF configuration template.
* The OSPF configuration module is automatically removed from a node that does not run OSPF on any non-loopback interface or VRF. In that case, _netlab_ generates a warning that can be turned off by setting **‌defaults.ospf.warnings.inactive** to **‌False**.
```

(ospf-default-link)=
## Default Link Parameters

Unless the OSPF network type is specified with the **ospf.network_type**, it's set to **point-to-point** on links with exactly two non-host nodes attached to them and left unspecified otherwise (implying platform default, which is almost always **broadcast**).

When the **ospf.passive** attribute is not specified on a link or an interface, _netlab_ uses the link roles together with the link types to decide whether to include an interface in an OSPF process and whether to make an interface passive:

* External links (links with **role: external**) are not included in the OSPF process. 
* Links with **role** set to **passive** are configured as *passive* OSPF interfaces.
* Interfaces connected to links with a single router or routing daemon attached are *passive* OSPF interfaces.

**Notes:** 

* The BGP module could set the link role. Links with devices from different AS numbers attached to them get a role specified in **defaults.bgp.ebgp_role** parameter. The system default value of that parameter is **external**, excluding inter-AS links from the OSPF process.
* Management interfaces are never added to the OSPF process. They are not in the set of device links and, thus, not considered in the OSPF configuration template.

(ospf-default)=
## Specifying External Default Route

The **ospf.default** parameter specifies that the device should originate an external (E1 or E2) default route into an OSPF domain. It can be set to **true** or **false**; you can also be more specific and use the following settings:

* **ospf.default.always**: set to *True* when you want the device to originate an OSPF default route, even when it does not have a default route itself.
* **ospf.default.cost**: set the cost of the originated default route
* **ospf.default.type**: the OSPF type of the external default route (`e1` or `e2`).

## Example

We want to create a three-router multi-area OSPF network:

* R1 is a backbone area router
* R2 is ABR between the backbone area and area 1
* R3 is in an intra-area router in area 1.

All devices run OSPF:
```
module: [ ospf ]
```

The default OSPF area is 0.0.0.0:
```
ospf:
  area: 0.0.0.0
```

R1 and R2 are in default OSPF area (no need to specify per-node area):

```
nodes:
  r1:
    device: iosv
  r2:
    device: eos
```

R3 is in area 1. Non-default OSPF area must be specified within node data:

```
nodes:
  r3:
    device: nxos
    ospf:
      area: 0.0.0.1
```

The link between R1 and R2 is in area 0. No need to specify per-link area:

```
links:
- r1:
  r2:
```

The link between R2 and R3 is in area 1. Specify the OSPF area within the link definition:

```
links:
- r2:
  r3:
  ospf:
    area: 0.0.0.1
```

Alternatively, you could specify the OSPF area just for R2 (as R3 is already in area 1):

```
links:
- r2:
    ospf:
      area: 0.0.0.1
  r3:
```

**Interesting details**:

* The default value for interface OSPF area is the node OSPF area
* The default value for node OSPF area is the global OSPF area (default value: 0.0.0.0).
* Due to the propagation of default values, the OSPF area for the R2-R3 link would be area 0 on R2 and area 1 on R3 -- you have to specify the OSPF area within the link definition or an individual node connected to the link.

### Resulting Device Configurations

The above topology generates the following device configurations:

#### R1 (Cisco IOS)

```
router ospf 1
!
interface Loopback0
 ip ospf 1 area 0.0.0.0
!
interface GigabitEthernet0/1
 ip ospf 1 area 0.0.0.0
 ip ospf network point-to-point
```

#### R2 (Arista EOS)

```
router ospf 1
!
interface Loopback0
 ip ospf area 0.0.0.0
!
interface Ethernet1
 ip ospf area 0.0.0.0
 ip ospf network point-to-point
!
interface Ethernet2
 ip ospf area 0.0.0.1
 ip ospf network point-to-point
```

#### R3 (Cisco Nexus-OS)

```
feature ospf
!
router ospf 1
!
interface loopback0
 ip router ospf 1 area 0.0.0.1
!
interface Ethernet1/1
 ip router ospf 1 area 0.0.0.1
 ip ospf network point-to-point
```

### Complete network topology:

```
module: [ ospf ]

ospf:
  area: 0.0.0.0

nodes:
  r1:
    device: iosv
  r2:
    device: eos
  r3:
    device: nxos
    ospf:
      area: 0.0.0.1

links:
- r1:
  r2:

- r2:
  r3:
  ospf:
    area: 0.0.0.1
```
