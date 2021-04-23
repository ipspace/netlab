# Simple BGP Example

We want to create a three-router BGP network:

* PE1 and PE2 are in AS 65000
* E1 is in AS 65001

All devices run BGP and OSPF (we need OSPF within AS 65000 to propagate loopback interfaces):

```
module: [ bgp,ospf ]
```

Default BGP AS number is 65000. Default OSPF area is 0.0.0.0. Default device type is Cisco IOSv:

```
bgp:
  as: 65000 
ospf:
  area: 0.0.0.0
defaults:
  device: iosv
```

PE1 and PE2 are in the default BGP AS and default OSPF area:

```
nodes:
  pe1:
  pe2:
```

E1 is an Arista EOS device in BGP AS 65001:

```
nodes:
  e1:
    device: eos
    bgp:
      as: 65001 
```

There are links between PE1 and PE2, and between PE2 and E1. The link between PE2 and E1 will be automatically tagged as *external*. OSPF in area 0 will be configured on the pe1-pe2 link.

```
links:
- pe1-pe2
- pe2-e1
```


### Resulting Data Structures

This is the BGP-related part of transformed node data on PE1. It's extremely easy to generate BGP configuration out of it:

```
- bgp:
    as: 65000
    neighbors:
    - as: 65000
      ipv4: 10.0.0.2
      name: pe1
      type: ibgp
    - as: 65001
      ipv4: 10.1.0.5
      name: e1
      type: ebgp
    next_hop_self: true
```

Interface information on PE1 includes the link role (*external*) which the OSPF configuration module uses to determine whether to include an interface in the OSPF process.

```
  links:
  - ifindex: 1
    ifname: GigabitEthernet0/1
    ipv4: 10.1.0.2/30
    linkindex: 1
    name: pe2 -> pe1
    neighbors:
      pe1:
        ifname: GigabitEthernet0/1
        ipv4: 10.1.0.1/30
    remote_id: 2
    remote_ifindex: 1
    type: p2p
  - ifindex: 2
    ifname: GigabitEthernet0/2
    ipv4: 10.1.0.6/30
    linkindex: 2
    name: pe2 -> e1
    neighbors:
      e1:
        ifname: Ethernet1
        ipv4: 10.1.0.5/30
    remote_id: 1
    remote_ifindex: 1
    role: external
    type: p2p
```

### Resulting Device Configurations

The above topology generates the following device configurations

#### PE1 (Cisco IOS)

```
interface Loopback0
 ip address 10.0.0.2 255.255.255.255
 ip ospf 1 area 0.0.0.0
!
interface GigabitEthernet0/1
 description pe1 -> pe2
 ip address 10.1.0.1 255.255.255.252
 ip ospf network point-to-point
 ip ospf 1 area 0.0.0.0
!
router ospf 1
!
router bgp 65000
 bgp log-neighbor-changes
 neighbor 10.0.0.3 remote-as 65000
 neighbor 10.0.0.3 description pe2
 neighbor 10.0.0.3 update-source Loopback0
 !
 address-family ipv4
  network 10.0.0.2 mask 255.255.255.255
  neighbor 10.0.0.3 activate
  neighbor 10.0.0.3 next-hop-self
 exit-address-family
 ```

#### PE2 (Cisco IOS)

```
interface Loopback0
 ip address 10.0.0.3 255.255.255.255
 ip ospf 1 area 0.0.0.0
!
interface GigabitEthernet0/1
 description pe2 -> pe1
 ip address 10.1.0.2 255.255.255.252
 ip ospf network point-to-point
 ip ospf 1 area 0.0.0.0
!
interface GigabitEthernet0/2
 description pe2 -> e1 [external]
 ip address 10.1.0.6 255.255.255.252
!
router ospf 1
!
router bgp 65000
 bgp log-neighbor-changes
 neighbor 10.0.0.2 remote-as 65000
 neighbor 10.0.0.2 description pe1
 neighbor 10.0.0.2 update-source Loopback0
 neighbor 10.1.0.5 remote-as 65001
 neighbor 10.1.0.5 description e1
 !
 address-family ipv4
  network 10.0.0.3 mask 255.255.255.255
  network 10.1.0.0 mask 255.255.255.252
  neighbor 10.0.0.2 activate
  neighbor 10.0.0.2 next-hop-self
  neighbor 10.1.0.5 activate
 exit-address-family
```

#### E1 (Arista EOS)

```
interface Ethernet1
   description e1 -> pe2 [external]
   ip address 10.1.0.5/30
!
interface Loopback0
   ip address 10.0.0.1/32
   ip ospf area 0.0.0.0
!
router bgp 65001
   neighbor 10.1.0.6 remote-as 65000
   neighbor 10.1.0.6 description pe2
   !
   address-family ipv4
      neighbor 10.1.0.6 activate
      network 10.0.0.1/32
!
router ospf 1
   interface unnumbered hello mask tx 0.0.0.0
```

### Complete network topology

```
module: [ bgp,ospf ]

bgp:
  as: 65000
ospf:
  area: 0.0.0.0
defaults:
  device: iosv

nodes:
  pe1:
  pe2:
  e1:
    device: eos
    bgp:
      as: 65001
links:
- pe1-pe2
- pe2-e1
```
