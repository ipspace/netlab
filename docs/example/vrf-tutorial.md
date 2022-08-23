# Defining and Using VRFs

This tutorial explains the various ways you can define and use VRFs implemented in the [VRF configuration module](../module/vrf.md).

To use VRFs in your networking labs:

* Add **vrf** module to all nodes that have VRF instances
* [Define VRFs](module-vrf-definition) in network topology or within individual nodes
* [Attach device interfaces to VRFs](module-vrf-interface) with the **vrf** link or interface (node-to-link attachment) attribute.

This document starts with an easy walk through simple VRF designs and gets progressively more complex, ending with overlapping and common services VPNs. Topologies described in this document were tested on Cisco IOSv and Arista vEOS; source files are [available on GitHub](https://github.com/ipspace/netsim-examples/tree/master/VRF).

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Simple Isolated VRFs

Let's start with two isolated VRFs: *red* and *blue*. We could ignore all details (route distinguishers and route targets); *netlab* will auto-generate all required values.

```
vrfs:
  red:
  blue:
  
nodes:
  rtr:
    module: [ vrf ]
```

A VRF without an **rd** attribute gets an auto-generated RD. The AS part of the RD is the value of **bgp.as** or **vrf.as** attribute. The system default value of **vrf.as** attribute is 65000, which means that without additional parameters our VRFs get RD values 65000:1 (red) and 65000:2 (blue).

*netlab* uses simple isolated VRFs as the default connectivity model:

* A VRF without an **export** attribute gets a single export route target equal to the VRF RD.
* Likewise, a VRF without an **import** attribute gets a single import route target equal to VRF RD.

The final data structure describing VRFs in our lab topology is thus:

```
vrfs:
  blue:
    export:
    - '65000:2'
    import:
    - '65000:2'
    rd: '65000:2'
  red:
    export:
    - '65000:1'
    import:
    - '65000:1'
    rd: '65000:1'
```

**Notes:** 

* Auto-generated RD values are assigned to VRFs in the original order (red before blue).
* Attributes in *netlab*-generated YAML files are sorted alphabetically (blue before red).
* RD/RT values (N:N) should be in single or double quotes to ensure PyYAML module treats them as strings.

## Specifying RD and RT Values

You can specify any subset of RD/RT values in VRF definitions, and the rest of the values will be auto-generated. For example, you could specify RD in the *red* VRF and RT in the *blue* VRF:

```
vrfs:
  red:
    rd: "1:1"
  blue:
    import: [ "2:2" ]
```

**Notes**: 

* You MUST use quotes around RD/RT values. PyYAML interprets "1:1" as number 11.
* If you plan to extend the lab configuration with import/export route maps, set **import** and **export** attributes to empty lists.

Please note that the RT values **are not** used to generate RD. While the *red* VRF gets the desired import/export route targets, the RD for VRF *blue* is auto-generated, resulting in the following setup that might not be what you're looking for:

```
vrfs:
  blue:
    export:
    - '65000:1'
    import:
    - '2:2'
    rd: '65000:1'
  red:
    export:
    - '1:1'
    import:
    - '1:1'
    rd: '1:1'
```

## Using VRFs on Interfaces

All you have to do to make an interface part of a VRF is to use **vrf** attribute in interface (node-to-link attachment) data. The value of the **vrf** attribute is the VRF name, for example:

```
vrfs:
  red:

nodes:
  rtr:
    module: [ vrf ]
  h1:
  h2:

links:
- rtr: { vrf: red }
  h1:
- rtr: { vrf: red }
  h2:
```

**Notes:**

* The node with a VRF interface must use the **vrf** module

A **vrf** attribute specified on a link is inherited by all interfaces attached to that link -- an ideal scenario for a VRF Lite core link:

```
vrfs:
  red:
  blue:

module: [ vrf,ospf ]

nodes:
  pe1:
  pe2:

links:
- name: PE-to-PE link in VRF red
  vrf: red
  pe1:
  pe2:
```

## EBGP Sessions with CE-Routers

If you want to use EBGP sessions with CE-routers within a VRF you have to:

* Add [**bgp** configuration module](../module/bgp.md) to PE- and CE-routers
* Specify different AS numbers for PE- and CE-routers (IBGP VRF sessions will not work)
* Add PE-to-CE links to VRFs on the PE-routers.

The following topology builds a simple single-VRF network with EBGP running between PE- and CE-routers:

```
vrfs:
  blue:

module: [ vrf,ospf,bgp ]
bgp.as: 65000

nodes:
  pe1:
  pe2:
  cb1:
    module: [ bgp ]
    bgp.as: 65101
  cb2:
    module: [ bgp ]
    bgp.as: 65102

links:
- pe1: { vrf: blue }
  cb1:
- pe2: { vrf: blue }
  cb1:
- pe1: { vrf: blue }
  cb2:
- pe2: { vrf: blue }
  cb2:
- pe1:
  pe2:
```

**Notes:**
* The EBGP sessions between PE1 and PE2, and CB1 and CB2 will be configured within the VRF address family on PE1 and PE2.
* A global IPv4/IPv6 IBGP session will be configured between PE1 and PE2.
* The global IBGP session will not carry VPNv4 prefixes unless you add **mpls.vpn** (see example below) module to PE1 and PE2.

Behind the scenes, the VRF configuration module removes EBGP neighbors reachable through VRF interfaces from the global list of BGP neighbors on the PE-routers (so they won't be configured as part of the BGP routing process) and adds them to VRF data structure:

```
nodes:
  pe1:
    vrfs:
      blue:
        af:
          ipv4: true
        bgp:
          neighbors:
          - as: 65101
            ifindex: 3
            ipv4: 10.1.0.9
            name: cb1
            type: ebgp
          - as: 65102
            ifindex: 4
            ipv4: 10.1.0.17
            name: cb2
            type: ebgp
        export:
        - '65000:2'
        import:
        - '65000:2'
        rd: '65000:2'
        vrfidx: 101
```

The BGP neighbors specified in the VRF data structure are then configured within the VRF BGP address family.

## Running OSPF with CE-Routers

OSPF is enabled on all internal (intra-AS) interfaces on every node with [**ospf** configuration module](../module/ospf.md). To disable OSPF on an individual link or interface, set link/interface **ospf** attribute to *False*.

The VRF configuration module removes OSPF data from VRF interfaces and recreates a list of OSPF interface within VRF data structure. The VRF interfaces are thus not included in the global OSPF process, and the VRF configuration templates create per-VRF OSPF processes as needed.

The VRF configuration templates also configure an automatic two-way redistribution between BGP and OSPF when it finds OSPF-enabled VRF interfaces and **bgp.as** defined in the node data.

For example, the following topology enables OSPF between PE- and CE-routers in VRF red:

```
vrfs:
  red:

module: [ vrf,ospf,bgp ]
bgp.as: 65000

nodes:
  pe1:
  pe2:
  cr1:
    module: [ ospf ]
  cr2:
    module: [ ospf ]

links:
- pe1: { vrf: red }
  pe2: { vrf: red }
  cr1:
  ospf.cost: 10
- pe1: { vrf: red }
  cr2:
  ospf.cost: 10
- pe2: { vrf: red }
  cr2:
  ospf.cost: 10
```

The resulting Cisco IOS configuration includes BGP routing, OSPF routing and two-way redistribution:

```
router bgp 65000
 address-family ipv4 vrf red
  redistribute connected
  redistribute ospf 100
!
router ospf 100 vrf red
 router-id 10.0.0.1
 redistribute bgp 65000 subnets
!
interface Loopback100
 ip ospf 100 area 0.0.0.0
!
interface GigabitEthernet0/1
! pe1 -> [pe2,cr1]
 ip ospf 100 area 0.0.0.0
 ip ospf cost 10
!
interface GigabitEthernet0/2
! pe1 -> cr2
 ip ospf 100 area 0.0.0.0
 ip ospf network point-to-point
 ip ospf cost 10
```

## VPNv4 Prefixes
If you want to carry VPNv4 (or VPNv6) prefixes, you have to enable **mpls.vpn** (and a MPLS label protocol, such as **mpls.ldp**).

The following example expands the *EBGP Sessions with CE-Routers* configuration:
```
vrfs:
  blue:

module: [ vrf,ospf,bgp,mpls ]
bgp.as: 65000

nodes:
  pe1:
    mpls:
      vpn: true
      ldp: true
  pe2:
     mpls:
       vpn: true
       ldp: true
  cb1:
    module: [ bgp ]
    bgp.as: 65101
  cb2:
    module: [ bgp ]
    bgp.as: 65102
  cb3:
    module: [ bgp ]
    bgp.as: 65103
  cb4:
    module: [ bgp ]
    bgp.as: 65104

links:
- pe1:
  pe2:
- pe1: { vrf: blue }
  cb1:
- pe2: { vrf: blue }
  cb1:
- pe1: { vrf: blue }
  cb2:
- pe2: { vrf: blue }
  cb2:
- pe1: { vrf: blue }
  cb3:
- pe2: { vrf: blue }
  cb4:
```