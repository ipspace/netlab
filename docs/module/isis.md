# IS-IS Configuration Module

This configuration module configures IS-IS routing process on Cisco IOS, Cisco NX-OS, Arista EOS and Junos (tested on vSRX).

Supported IS-IS features:

* IPv4 and IPv6
* IS type (L1 and/or L2)
* Multi-topology IPv6 (enabled by default as soon as the node has at least one IPv6 address, cannot be disabled)
* Wide metrics (enabled by default, cannot be disabled)
* Unnumbered point-to-point interfaces
* Passive interfaces

**Notes:**
* On Arista EOS, IPv6 is enabled on all interfaces as soon as one interface has an IPv6 address. Arista EOS implementation of IS-IS refuses to work on interfaces with missing address families.

### Global Parameters

* **isis.area** -- CLNS area prefix. Router address (NET) is computed from area prefix, 6-byte system ID (using **id** node attribute) and NSAP selector (.00)
* **isis.type** -- IS-IS router type (default: **level-2**)

### Node Parameters

You can specify node parameters as global values (top-level topology elements) or within individual nodes. You can also specify **isis.net** on individual nodes instead of using **isis.area** (see [example](#example) for details).

**Note:**
* When specifying **isis.net**, avoid values in range *area.0000.0000.0001.00* through *area.0000.0000.0099.00* as they are used for auto-generated NETs.

### Link Parameters

* **isis.type** -- Link type (L1/L2/L1-2). Recognized as a valid attribute but not implemented. Please feel free to fix the configuration templates and submit a pull request.
* **isis.metric** or **isis.cost** -- Interface cost. Both parameters are recognized to make IS-IS configuration similar to OSPF (*metric* takes precedence over *cost*)

### Other Parameters

Link type is used to set IS-IS network type:

* *P2P link* ⇒ **point-to-point** network
* Any other link type ⇒ **broadcast** network
* *Stub link* ⇒ passive interface

Stub links must have exactly one device attached to them. To create multi-router stub links, use **role: stub** link attribute (see below).

### Using Link Roles

Link roles are used together with link types to decide whether to include an interface in an IS-IS process, and whether to make an interface passive:

* External links (links with **role: external**) are not included in the IS-IS process. 
* Links with **role** set to **stub** or **passive** are configured as *passive* IS-IS interfaces.

**Notes:** 

* Link role could be set by the BGP module -- links with devices from different AS numbers attached to them get a role specified in **defaults.bgp.ebgp_role** parameter. The system default value of that parameter is **external**, making inter-AS links excluded from the IS-IS process.
* Management interfaces are never added to the IS-IS process. They are not in the set of device links and thus not considered in the IS-IS configuration template.

## Example

We want to create a three-router multi-area IS-IS network:

* R1 and R2 are in area 49.0001
* R3 is in area 49.0002.

All devices run OSPF:
```
module: [ isis ]
```

Default IS-IS area is 49.0001:
```
isis:
  area: 49.0001
```

R1 and R2 are in default IS-IS area. We'll specify explicit NET for R2:

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

We'll specify asymmetric per-node IS-IS metrics on link between R2 and R3:

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

The above topology generates the following device configurations

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
