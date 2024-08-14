(module-isis)=
# IS-IS Configuration Module

This configuration module configures the IS-IS routing process on Cisco IOS, Cisco NX-OS, Arista EOS, Junos (tested on vSRX), Nokia SR OS, and Nokia SR Linux.

The module supports the following IS-IS features:

* IPv4 and IPv6
* IS type (L1 and/or L2)
* Multi-topology IPv6 (enabled by default as soon as the node has at least one IPv6 address, cannot be disabled)
* Wide metrics (enabled by default, cannot be turned off)
* Unnumbered IPv4 interfaces
* Passive interfaces
* BFD


```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Platform Support

The following table describes per-platform support of individual IS-IS features:

| Operating system      | IS type | IPv6 AF | Multi<br>topology | Unnumbered<br />interfaces | IPv4<br />BFD | IPv6<br />BFD |
| ------------------ | :-: | :-: | :-: | :-: | :-: | :-: |
| Arista EOS         | ✅  | ✅  | ✅  | ✅  | ✅  | ❌  |
| Cisco ASAv         | ✅  | ✅  | ✅  | ❌  | ❌  | ❌ |
| Cisco IOS          | ✅  | ✅  | ✅  | ✅  | ✅  | ✅ | 
| Cisco IOS XE[^18v] | ✅  | ✅  | ✅  | ✅  | ✅  | ✅ | 
| Cisco IOS XRv      | ✅  | ✅  | ✅  | ✅  |  ❌  |  ❌ |
| Cisco Nexus OS     | ✅  | ✅  | ✅  | ✅  | ✅  |  ❌ |
| FRR                | ✅  | ✅  | ✅  | ✅  | ❌  | ❌ |
| Junos[^Junos]      | ✅  | ✅  | ✅  | ✅  | ✅  | ✅ |
| Nokia SR Linux     | ✅  | ✅  | ❌  | ✅  | ✅  | ✅ | 
| Nokia SR OS        | ✅  | ✅  | ✅  | ✅  | ✅  | ✅ | 
| VyOS               | ✅  | ✅  | ❌  |  ❌  | ✅  | ✅ |

[^18v]: Includes Cisco CSR 1000v and Cisco Catalyst 8000v

[^Junos]: Includes vMX, vSRX, vPTX and vJunos-switch

**Notes:**
* On Arista EOS, IPv6 is enabled on all interfaces as soon as one has an IPv6 address. Arista EOS implementation of IS-IS refuses to work on interfaces with missing address families.
* On VyOS, IPv6 is enabled on all interfaces as soon as one has an IPv6 address.
* Cisco ASA does not support P2P IS-IS links. You could add `isis.network_type: false` to point-to-point links connecting ASA to other devices.

```{tip}
See [IS-IS Integration Tests Results](https://release.netlab.tools/_html/coverage.isis) for more details.
```

## Global Parameters

* **isis.area** -- CLNS area prefix. Router address (NET) is computed from area prefix, 6-byte system ID (using **id** node attribute), and NSAP selector (.00)
* **isis.type** -- IS-IS router type (**level-1**, **level-2** or **level-1-2**. Default: **level-2**)
* **isis.bfd** -- enable BFD for IS-IS. This parameter could be a boolean value (*True*/*False*) or a dictionary of address families, for example:

```
isis:
  area: "49.0002"
  bfd:
    ipv4: True
    ipv6: True
```

```{warning}
Specify **‌isis.area** with a single dot (example: 49.0001) within quotes to tell the YAML parser it's not a floating-point number.
```

## Node Parameters

You can specify node parameters as global values (top-level topology elements) or within individual nodes. You can specify **isis.net** on individual nodes instead of using **isis.area** (see [example](#example) for details).

**Note:**
* When specifying **isis.net**, avoid values in range *area.0000.0000.0001.00* through *area.0000.0000.0099.00* as they are used for auto-generated NETs.

IS-IS is automatically started on all interfaces within an autonomous system (interfaces with no EBGP neighbors; see also [](routing_external)). To disable IS-IS on an intra-AS link, set the **isis** link parameter to *False* (see also [](routing_disable)).

```{tip}
The IS-IS configuration module is automatically removed from a node that does not run IS-IS on any non-loopback interface. In that case, _netlab_ generates a warning that can be turned off by setting **‌defaults.isis.warnings.inactive** to **‌False**.
```

## Link Parameters

* **isis.type** -- Link type (**level-1**, **level-2** or **level-1-2**). Recognized as a valid attribute but not implemented. Please feel free to fix the configuration templates and submit a pull request.
* **isis.network_type** -- Set IS-IS network type. Valid values are **point-to-point** or *False* (do not set the network type). See also [Default Link Parameters](#default-link-parameters).
* **isis.metric** or **isis.cost** -- Interface cost. Both parameters are recognized to make IS-IS configuration similar to OSPF (*metric* takes precedence over *cost*)
* **isis.bfd** -- enable or disable BFD on individual interfaces. Like with the node-level **isis.bfd** parameter, this parameter could be a boolean value (*True* to enable BFD for all address families, *False* to disable IS-IS BFD on the interface) or a dictionary of address families, for example:

Example:

```
links:
- name: Link with IPv4-only BFD
  sros_r1:
  srlinux_r2:
  isis.bfd:
    ipv4: True
    ipv6: False
```

## Default Link Parameters

The number of neighbors on an interface is used to set IS-IS network type unless it's specified with **isis.network_type** link or interface attribute. Interfaces with exactly one non-host neighbor (point-to-point links) have **isis.network_type** set to **point-to-point**. 

When the **isis.passive** interface parameter is not set on a link or an interface, _netlab_ uses the link roles together with  the link types to decide whether to include an interface in an IS-IS process and whether to make an interface passive:

* External links (links with **role: external**) are not included in the IS-IS process. 
* Links with **role** set to **passive** are configured as *passive* IS-IS interfaces.
* Interfaces connected to links with a single router or routing daemon attached are *passive* IS-IS interfaces.

**Notes:** 

* The BGP module could set link role. Links with devices from different AS numbers attached to them get a role specified in **defaults.bgp.ebgp_role** parameter. The system default value of that parameter is **external**, excluding inter-AS links from the IS-IS process.
* Management interfaces are never added to the IS-IS process. They are not in the set of device links and, thus, not considered in the IS-IS configuration template.

## Example

We want to create a three-router multi-area IS-IS network:

* R1 and R2 are in area 49.0001
* R3 is in area 49.0002.

All devices run OSPF:
```
module: [ isis ]
```

The default IS-IS area is 49.0001:
```
isis:
  area: 49.0001
```

R1 and R2 are in the default IS-IS area. We'll specify explicit NET for R2:

```
nodes:
  r1:
    device: iosv
  r2:
    device: eos
    isis:
      net: 49.0001.0000.cafe.0002.00 
```

R3 is in area 49.0002.

```
nodes:
  r3:
    device: nxos
    isis:
      area: 49.0002
```

Each router has a stub interface:

```
links:
- r1:
- r2:
- r3:
```

We'll specify per-link IS-IS metric on the link between R1 and R2:

```
links:
- isis:
	  metric: 10
	r1:
  r2:
```

We'll specify asymmetric per-node IS-IS metrics on the link between R2 and R3:

```
links:
- r2:
    isis:
      metric: 20 
  r3:
    isis:
      metric: 30 
```

### Resulting Device Configurations

The above topology generates the following device configurations:

#### R1 (Cisco IOS)

```
router isis Gandalf
  log-adjacency-changes
  hostname dynamic
  is-type level-2
  metric-style wide
  net 49.0001.0000.0000.0001.00
  passive-interface GigabitEthernet0/1
  address-family ipv4 unicast
!
interface Loopback0
  ip router isis Gandalf
!
interface GigabitEthernet0/1
  ip router isis Gandalf
!
interface GigabitEthernet0/2
  ip router isis Gandalf
  isis metric 10
```

#### R2 (Arista EOS)

```
router isis Gandalf
  log-adjacency-changes
  is-hostname r2
  is-type level-2
  net 49.0001.0000.cafe.0002.00
  address-family ipv4 unicast
!
interface Loopback0
  isis enable Gandalf
!
interface Ethernet1
  isis enable Gandalf
  isis passive
!
interface Ethernet2
  isis enable Gandalf
  isis metric 10
!
interface Ethernet3
  isis enable Gandalf
  isis metric 20
```

#### R3 (Cisco Nexus OS)

```
feature isis
!
router isis Gandalf
  log-adjacency-changes
  is-type level-2
  hostname dynamic
  net 49.0002.0000.0000.0003.00
  address-family ipv4 unicast
!
interface Loopback0
  ip router isis Gandalf
!
interface Ethernet1/1
  ip router isis Gandalf
  isis passive-interface level-1-2
!
interface Ethernet1/2
  ip router isis Gandalf
  isis metric 30 level-1
  isis metric 30 level-2
```

### Complete Network Topology

```
module: [ isis ]

isis:
  area: 49.0001

nodes:
  r1:
    device: iosv
  r2:
    device: eos
    isis:
      net: 49.0001.0000.cafe.0002.00 
  r3:
    device: nxos
    isis:
      area: 49.0002

links:
- r1:
- r2:
- r3:
- isis:
	  metric: 10
	r1:
  r2:
- r2:
    isis:
      metric: 20 
  r3:
    isis:
      metric: 30 
```
