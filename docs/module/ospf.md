# OSPF Configuration Module

This configuration module configures OSPFv2 and OSPFv3 routing processes on most supported platforms (see supported features table).

Supported features:

* OSPFv2 and/or OSPFv3 (see platform support table and [address families](routing.md#address-families))
* Multi-area deployment
* Per-link cost and asymmetric costs
* OSPF network type
* Reference bandwidth
* Unnumbered point-to-point interfaces
* [Passive interfaces](routing.md#passive-interfaces)
* [Static router ID](routing.md#router-id)
* BFD

Missing features:

* Stub and NSSA areas
* Virtual links
* Opaque LSA
* Multi-area adjacencies
* Demand circuits
* A gazillion nerd knobs and IETF quirks

Need one of those? Create a plugin and contribute it.

The following table describes per-platform support of individual router-level OSPF features:

| Operating system         | Areas | Reference<br/>bandwidth | OSPFv3 | BFD  |
| ------------------------ | :---: | :---------------------: | :----: | :--: |
| Arista EOS               |   ✅  |            ✅          |   ✅   |  ✅  |
| Cisco IOS                |   ✅  |            ✅          |   ✅   |  ✅  |
| Cisco IOS XE             |   ✅  |            ✅          |   ✅   |  ✅  |
| Cisco Nexus OS           |   ✅  |            ✅          |   ❌   |  ✅  |
| Cumulus Linux            |   ✅  |            ✅          |   ❌   |  ❌  |
| Cumulus Linux 5.0 (NVUE) |   ✅  |            ✅          |   ❌   |  ❌  |
| Fortinet FortiOS         |   ❗  |            ✅          |   ❌   |  ❌  |
| FRR 7.5.0                |   ✅  |            ✅          |   ✅   |  ❌  |
| Juniper vSRX 3.0         |   ✅  |            ✅          |   ❌   |  ✅  |
| Mikrotik CHR RouterOS    |   ✅  |            ❌          |   ❌   |  ✅  |
| Nokia SR Linux           |   ✅  |            ✅          |   ❌   |  ✅  |
| Nokia SR OS              |   ✅  |            ✅          |   ❌   |  ✅  |
| VyOS                     |   ✅  |            ✅          |   ✅   |  ✅  |

**Notes:**
* Fortinet implementation of OSPF configuration module does not implement per-interface OSPF areas. All interfaces belong to the OSPF area defined in the node data.
* Mikrotik RouterOS and VyOS support BFD on OSPF only with the system default values for interval and multiplier.

The following table documents the interface-level OSPF features:

| Operating system         | Cost  | Network<br />type | Unnumbered<br />interfaces | Passive<br />interfaces |
| ------------------------ | :---: | :---------------: | :------------------------: | :---------------------: |
| Arista EOS               |   ✅  |         ✅        |             ✅            |            ✅           |
| Cisco IOS                |   ✅  |         ✅        |             ❗            |            ✅           |
| Cisco IOS XE             |   ✅  |         ✅        |             ✅            |            ✅           |
| Cisco Nexus OS           |   ✅  |         ✅        |             ✅            |            ✅           |
| Cumulus Linux            |   ✅  |         ✅        |             ✅            |            ✅           |
| Cumulus Linux 5.0 (NVUE) |   ✅  |         ✅        |             ✅            |            ✅           |
| Fortinet FortiOS         |   ✅  |         ❗        |             ✅            |            ✅           |
| FRR 7.5.0                |   ✅  |         ✅        |             ✅            |            ❗           |
| Juniper vSRX 3.0         |   ✅  |         ✅        |             ✅            |            ✅           |
| Mikrotik CHR RouterOS    |   ✅  |         ✅        |             ❌            |            ✅           |
| Nokia SR Linux           |   ✅  |         ✅        |             ❌            |            ✅           |
| Nokia SR OS              |   ✅  |         ✅        |             ✅            |            ✅           |
| VyOS                     |   ✅  |         ✅        |             ❌            |            ✅           |

Notes:
* Arista EOS, Cisco Nexus OS, and SR Linux support point-to-point and broadcast network types. Other network types will not be configured.
* SR OS supports point-to-point, broadcast and non-broadcast network types. Point-to-multipoint network type will not be configured.
* Cisco IOSv (release 15.x) does not support unnumbered IPv4 interfaces
* FRR does not support passive interfaces with OSPFv3
* Fortinet configuration templates set OSPF network type based on number of neighbors, not based on **ospf.network_type** link/interface parameter.

## Global Parameters

* **ospf.reference_bandwidth** sets the OSPF auto-cost reference bandwidth (in Mbps) for all devices in the network.

## Node Parameters

* **ospf.process** -- process ID (default: 1)
* **ospf.af** -- [OSPF address families](routing.md#address-families). Configures OSPFv2 and/or OSPFv3 on devices that support OSPFv3. Has no impact on other devices.
* **ospf.area** -- default OSPF area (default: 0.0.0.0). Used on links without explicit OSPF area, and on loopback interface.
* **ospf.reference_bandwidth** -- per-node OSPF auto-cost reference bandwidth (in Mbps).
* **ospf.bfd** -- enable BFD for OSPF (default: False)
* **ospf.router_id** -- set [static router ID](routing.md#router-id).

You can specify most node parameters as global values (top-level topology elements) or within individual nodes (see [example](#example) for details).

## Link Parameters

* **ospf.cost** -- OSPF cost
* **ospf.area** -- OSPF area. Use on ABRs; node-level OSPF area is recommended for intra-area routers.
* **ospf.network_type** -- Set OSPF network type. Allowed values are **point-to-point**, **point-to-multipoint**, **broadcast** and **non-broadcast**. See also [Default Link Parameters](#default-link-parameters)
* **ospf.bfd** -- enable or disable BFD for OSPF on an individual link or interface (boolean value, overrides node **ospf.bfd** setting)
* **ospf.passive** -- explicitly enable or disable [passive interfaces](routing.md#passive-interfaces)

**Note:** the same parameters can be specified for individual link nodes.

OSPF configuration module also supports [passive interfaces](routing.md#passive-interfaces) and [external links](routing.md#external-interfaces).

```{tip}
Management interfaces are never added to the OSPF process. They are not in the set of device links and thus not considered in the OSPF configuration template.
```

## Default Link Parameters

Default OSPF network type (unless specified with **ospf-network_type** link/interface attribute) is set based on the number of nodes attached to the link:

* Two nodes (*P2P* link) ⇒ **point-to-point** network
* Any other link type ⇒ **broadcast** network

Stub links (links with exactly one device attached to them) are configured as passive OSPF interfaces. See also Using Link Roles (next section).

## Example

We want to create a three-router multi-area OSPF network:

* R1 is a backbone area router
* R2 is ABR between backbone area and area 1
* R3 is in intra-area router in area 1.

All devices run OSPF:
```
module: [ ospf ]
```

Default OSPF area is 0.0.0.0:
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

Link between R1 and R2 is in area 0. No need to specify per-link area:

```
links:
- r1:
  r2:
```

Link between R2 and R3 is in area 1. Specify OSPF area within link definition:

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

* The default value for interface OSPF area is the node OSPF area (specified in configuration template).
* The default value for node OSPF area is the global OSPF area (default value: 0.0.0.0).
* Due to the propagation of default values, the OSPF area for R2-R3 link would be area 0 on R2 and area 1 on R3. The OSPF area thus needs to be specified within link definition, or within an individual node connected to a link.

### Resulting Device Configurations

The above topology generates the following device configurations

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