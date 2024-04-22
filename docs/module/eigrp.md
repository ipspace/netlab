# EIGRP Configuration Module

This configuration module configures the EIGRP routing process on Cisco IOS, Cisco IOS-XE, and Cisco Nexus-OS.

Supported features:

* IPv4 and IPv6
* EIGRP AS number
* Unnumbered point-to-point interfaces (Cisco IOS/IOS-XE only)
* Passive interfaces

## Global Parameters

* **eigrp.as** sets the network-wide EIGRP AS number (default: 1)

## Node Parameters

* **eigrp.as** -- per-node EIGRP AS number (default: 1 -- inherited from global defaults)

```{tip}
The EIGRP configuration module is automatically removed from a node that does not run EIGRP on any non-loopback interface. In that case, _netlab_ generates a warning that can be turned off by setting **‌defaults.eigrp.warnings.inactive** to **‌False**.
```

## Link Parameters

* **eigrp.passive** -- Make this link/interface a passive interface regardless of the global passive interface rules (note: cannot be used to make an interface active).

## Using Link Roles

Link roles are used together with link types to decide whether to include an interface in an EIGRP process and whether to make an interface passive:

* External links (links with **role: external**) are not included in the IPv4 EIGRP process on Nexus OS, or in the IPv6 EIGRP processes.
* External links are configured as *passive* IPv4 EIGRP interfaces on Cisco IOS/IOS XE.

The following interfaces are also configured as passive EIGRP interfaces:

* Interfaces with **role** set to **passive**.
* Interfaces connected to links with a single router or routing daemon attached.

**Notes:** 

* The BGP module could set link role -- links with devices from different AS numbers attached to them get a role specified in **defaults.bgp.ebgp_role** parameter. The system default value of that parameter is **external**, making inter-AS links passive or excluded from the EIGRP process (see above).
* Management interfaces are never added to the Nexus-OS EIGRP processes or the IPv6 EIGRP process on Cisco IOS/IOS-XE. However, as the Cisco IOS/IOS-XE IPv4 EIGRP configuration uses **network 0.0.0.0 255.255.255.255** statement, the management interface could become part of an EIGRP process if it's not in the management VRF. The management interface is made *passive* to ensure there's no exchange of EIGRP updates over it.

## Example

We want to create a three-router EIGRP network testing IOS, IOS-XE, and Nexus OS EIGRP implementation.

All devices run EIGRP:

```
module: [ eigrp ]
```

We'll use EIGRP AS 2:

```
eigrp:
  as: 2
```

In our lab, we'll use IPv4 and IPv6 addressing. IPv6 addresses will be configured on loopback and LAN interfaces but not on P2P interfaces.

```
addressing:
  loopback:
    ipv4: 172.18.1.0/24
    ipv6: 2001:db8:0::/48
  lan:
    ipv4: 172.19.0.0/16
    ipv6: 2001:db8:1::/48
```

The lab has three nodes, each one of them running a different operating system:

```
nodes:
- name: r1
  device: iosv
- name: r2
  device: csr
- name: s1
  device: nxos
```

All three devices share a LAN interface with bandwidth set to 100 Mbps. Each device is also connected to one or two P2P links and a stub interface.

```
links:
- r1:
  r2:
  s1:
  bandwidth: 100000
- r1-r2
- r2-s1
- r1
- r2
- s1
```

### Resulting EIGRP Configurations

The above topology generates the following device configurations [^1].

[^1]: Interface descriptions and bandwidths are included in device configurations for documentation purposes, even though they are not part of the EIGRP configuration template.

#### R1 (Cisco IOS)

```
router eigrp 2
 network 0.0.0.0 255.255.255.255
 passive-interface GigabitEthernet0/3
 passive-interface GigabitEthernet0/0
!
ipv6 router eigrp 2
 passive-interface GigabitEthernet0/3
!
interface Loopback0
 ipv6 eigrp 2
!
interface GigabitEthernet0/1
 description r1 -> [r2,s1]
 bandwidth 100000
 ipv6 eigrp 2
!
interface GigabitEthernet0/2
 description r1 -> r2
!
interface GigabitEthernet0/3
 ipv6 eigrp 2
 description Stub interface
```

#### R2 (Cisco IOS-XE)

```
router eigrp 2
 network 0.0.0.0 255.255.255.255
 passive-interface GigabitEthernet5
 passive-interface GigabitEthernet1
!
ipv6 router eigrp 2
 passive-interface GigabitEthernet5
!
interface Loopback0
 ipv6 eigrp 2
!
interface GigabitEthernet2
 description r2 -> [r1,s1]
 bandwidth 100000
 ipv6 eigrp 2
!
interface GigabitEthernet3
 description r2 -> r1
!
interface GigabitEthernet4
 description r2 -> s1
!
interface GigabitEthernet5
 description Stub interface
 ipv6 eigrp 2
```

#### S1 (Cisco Nexus-OS)

```
feature eigrp
!
router eigrp 2
 address-family ipv6 unicast
!
interface loopback0
 ip router eigrp 2
 ipv6 router eigrp 2
!
interface Ethernet1/1
 description s1 -> [r1,r2]
 ip router eigrp 2
 ipv6 router eigrp 2
 bandwidth 100000
!
interface Ethernet1/2
 description s1 -> r2
 ip router eigrp 2
!
interface Ethernet1/3
 description Stub interface
 ip router eigrp 2
 ipv6 router eigrp 2
 ip passive-interface eigrp 2
 ipv6 passive-interface eigrp 2
```

### Complete network topology:

```
addressing:
  loopback:
    ipv4: 172.18.1.0/24
    ipv6: 2001:db8:0::/48
  lan:
    ipv4: 172.19.0.0/16
    ipv6: 2001:db8:1::/48

module: [ eigrp ]

eigrp:
  as: 2

nodes:
- name: r1
  device: iosv
- name: r2
  device: csr
- name: s1
  device: nxos

links:
- r1:
  r2:
  s1:
  bandwidth: 100000
- r1-r2
- r2-s1
- r1
- r2
- s1
```