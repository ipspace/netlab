# EIGRP Configuration Module

This configuration module configures the EIGRP routing process on Cisco IOSv, Cisco IOS-XE[^18v], and Cisco Nexus-OS.

[^18v]: Includes Cisco CSR 1000v, Cisco Catalyst 8000v, Cisco IOS-on-Linux (IOL), and IOL Layer-2 image.

Supported features:

* IPv4 and IPv6
* EIGRP AS number
* Unnumbered point-to-point interfaces (Cisco IOS-XE only)
* Passive interfaces

## Global Parameters

* **eigrp.as** sets the network-wide EIGRP AS number (default: 1)

## Node Parameters

* **eigrp.as** -- per-node EIGRP AS number (default: 1 -- inherited from global defaults)

```{tip}
The EIGRP configuration module is automatically removed from a node that does not run EIGRP on any non-loopback interface. In that case, _netlab_ generates a warning that can be turned off by setting **‌defaults.eigrp.warnings.inactive** to **‌False**.
```

## Link Parameters

* **eigrp.passive: True** -- Make this link/interface a passive interface
* **eigrp: False** -- Do not run EIGRP on this link/interface (see also [](routing_disable))

## Using Link Roles

Link roles are used together with link types to decide whether to include an interface in an EIGRP process and whether to make an interface passive:

* External links (links with **role: external**, see also [](routing_external)) are not included in the EIGRP process.
* Interfaces connected to links with **role: passive**, or links with a single router or routing daemon, are automatically marked as **passive**.
* Management interfaces are in the management VRF and are never added to the EIGRP processes.

## Example

We want to create a three-router EIGRP network testing IOS, IOS-XE, and Nexus OS EIGRP implementation.

All devices run EIGRP with AS 2:

```
module: [ eigrp ]
eigrp.as: 2
```

In our lab, we'll use IPv4 and IPv6 addressing. IPv6 addresses will be configured on loopback and LAN interfaces, but not on P2P interfaces.

```
addressing:
  loopback:
    ipv4: 172.18.1.0/24
    ipv6: 2001:db8:0::/48
  lan:
    ipv4: 172.19.0.0/16
    ipv6: 2001:db8:1::/48
```

The lab has three nodes, each of which is running a different operating system:

```
nodes:
  r1: { device: iosv }
  r2: { device: csr }
  s1: { device: nxos }
```

All three devices share a LAN interface with the bandwidth set to 100 Mbps. Each device is also connected to one or two P2P links and a stub interface.

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
 eigrp router-id 172.18.1.1
 network 172.18.1.1 0.0.0.0
 network 172.19.0.1 0.0.0.0
 network 10.1.0.1 0.0.0.0
 network 172.19.1.1 0.0.0.0
 passive-interface GigabitEthernet0/3
!
ipv6 router eigrp 2
 eigrp router-id 172.18.1.1
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
 description r1 -> stub [stub]
```

#### R2 (Cisco IOS-XE)

```
router eigrp 2
 network 10.1.0.2 0.0.0.0
 network 10.1.0.5 0.0.0.0
 network 172.18.1.2 0.0.0.0
 network 172.19.0.2 0.0.0.0
 network 172.19.2.2 0.0.0.0
 passive-interface GigabitEthernet5
 eigrp router-id 172.18.1.2
!
ipv6 router eigrp 2
 passive-interface GigabitEthernet5
 eigrp router-id 172.18.1.2
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
 description r2 -> stub [stub]
 ipv6 eigrp 2
```

#### S1 (Cisco Nexus-OS)

```
feature eigrp
!
router eigrp 2
  router-id 172.18.1.3
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
 description s1 -> stub [stub]
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
eigrp.as: 2

nodes:
  r1: { device: iosv }
  r2: { device: csr }
  s1: { device: nxos }

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