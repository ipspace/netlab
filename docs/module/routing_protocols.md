# Common Routing Protocol Parameters

Most routing protocol modules support the following parameters:

* [](routing_router_id)
* [](routing_af)
* [](routing_passive)
* [](routing_external)
* [](routing_disable)
* [](routing_import)

(routing_router_id)=
## Router ID

Router ID is configured with **router_id** node parameter (applies to all routing protocols) or with **_protocol_.router_id** node parameter (applies to the selected routing protocol). Router ID can be configured as an IPv4 address or as an integer.

The default **router_id** is taken from the IPv4 address of the loopback interface or the [**router_id** address pool](../example/addressing-tutorial.md#using-built-in-address-pools) if there's no usable IPv4 address on the loopback interface.

**Example:**

```
modules: [ ospf, bgp ]

nodes:
  r1:
    router_id: 10.0.0.1
  r2:
    ospf.router_id: 10.0.0.2
    bgp.router_id: 10.0.1.2
  r3:
```

* Router ID for R1 is configured for the whole device and used for OSPFv2/OSPFv3 and BGP
* OSPFv2/OSPFv3 router ID for R2 is 10.0.0.2. BGP router ID for R2 is 10.0.1.2
* Node ID for R3 is 3 (the third node in the **nodes** dictionary). The router ID for R3 is taken from the loopback interface (10.0.0.3 unless you changed the **loopback** address pool) or from the **router_id** address pool (10.0.0.3).

(routing_af)=
## Address Families

Configuration modules for all IGP routing protocols that support multiple address families (IS-IS, EIGRP) or multiple protocol instances (OSPFv2, OSPFv3) support **_protocol_.af** global- or node-level module parameter. The **af** parameter can be a list- or a dictionary of address families.

The default value of the **af** parameter is set based on address families configured on loopback- or physical interfaces -- an address family is enabled within an IGP configuration on a device if at least one interface on that device has an IP address from that address family.

**Example:**

```
module: [ isis,ospf ]
isis.af.ipv6: True

nodes:
  r1:
    isis.af: [ ipv4, ipv6 ]
  r2:
    isis.af.ipv4: True
  r3:
    isis.af:
      ipv4: True
      ipv6: False
  r4:
    isis.af:
  r5:
```

* IS-IS address families are enabled based on configured **isis.af** parameters
* **ospf.af** parameter is not set -- OSPFv2 or OSPFv3 are enabled based on address families used on individual nodes

The following IS-IS address families are configured on individual routers:

* **R1**: IPv4 and IPv6. The configured list of address families overrides the topology defaults
* **R2**: IPv4 and IPv6. Node- and global parameters are dictionaries and can be merged.
* **R3**: IPv4 only. The **isis.af** parameter is fully specified within the node data and explicitly disables IPv6 AF.
* **R4**: The **isis.af** parameter is set to an empty value and is, therefore, calculated from the address families.
* **R5**: IPv6 only (global default)

(routing_passive)=
## Passive Interfaces

An interface is configured as a *passive* interface (when supported by the routing protocol implementation) if:

* **_protocol_.passive** parameter is set to `True` on a link or interface.
* The link **type** is set to **stub** (a single device is attached to the link)
* The link **role** is set to **passive**
* A single router or routing protocol daemon is attached to the link.

This parameter applies to IGP protocols.

**Example:**

```
module: [ ospf ]

nodes: [ r1, r2 ]

links:
- r1:
  r2:
- r1:
- r1:
  r2:
  role: passive
- r1:
  r2:
    ospf.passive: True
- r1:
  r2:
    ospf.passive: False
  role: passive
```

* The first link is a transit link
* The second link is a stub link (single node attached to the link) ⇨ The corresponding interface on R1 is passive
* The third link has a **passive** role ⇨ passive interfaces on R1 and R2
* The fourth link is a transit link, but the **ospf.passive** value is set on R2  interface ⇨ regular interface on R1, passive interface on R2
* The last link has **passive** role, but the **ospf.passive** value is set to *False* on R2 interface ⇨ passive interface on R1, regular interface on R2.

(routing_external)=
## External Interfaces

Links with **role: external** are not included in the IGP routing processes. The  **external** role can be set with a link parameter or by the BGP module.

BGP module sets link role specified in **defaults.bgp.ebgp_role** on links connecting devices with different AS numbers. The system default value of that parameter is **external**, excluding inter-AS links from the IGP processes.

If you want to include external subnets into your IGP (and disable BGP **next_hop_self** processing), set **defaults.bgp.ebgp_role** to **passive**.

```{warning}
The BGP module sets the link role on direct links and global VLANs but not on VLANs defined on a single node.

As a workaround, set the **‌nodes._node_.vlans._name_.role** node VLAN parameter to **‌external** on inter-AS VLANs defined on a single node.
```

(routing_disable)=
## Disabling a Routing Protocol on a Link/Interface

IGP protocols are usually configured on all internal interfaces (see [](routing_external) for more details). You can disable an IGP protocol on a link or an individual interface with the **_protocol_: False** attribute, for example:

```
module: [ ospf ]

nodes:
  r1:
  r2:

links:
- r1:
  r2:
  ospf: False       # Disable OSPF on R1 and R2 interfaces
- r1:
    ospf: False     # Disable OSPF on R1 interface
  r2:               # OSPF is still enabled on R2 interface
```

You can also disable EBGP sessions on a link or an individual interface with the **bgp: False** attribute, for example:

```
module: [ bgp ]

defaults.device: iosv

nodes:
  r1:
    bgp.as: 65000
  r2:
    bgp.as: 65101

links:
- r1:
  r2:
  name: Regular EBGP
- r1:
  r2:
  bgp: False
  name: No EBGP session
```

You cannot influence IBGP sessions with interface- or link attributes; you must use [advanced BGP node parameters](bgp-advanced-node).

(routing_disable_vrf)=
## Disabling a Routing Protocol in VRF

You can disable a VRF instance of OSPF or BGP with **ospf: False** or **bgp: False** VRF parameter.

In the following example, OSPF will be configured in `o_1` but not in `o_2`:

```
module: [ ospf, vrf ]

defaults.device: eos

vrfs:
  o_1:
  o_2:
    ospf: False

nodes:
  r1:
  r2:

links:
- r1:
  r2:
  vrf: o_1            # VRF OSPF is active between r1 and r2
- r1:
  r2:
  vrf: o_2            # No OSPF instance in o_2
```

(routing_import)=
## Importing Routes into a Routing Protocol

Some routing protocols support route import (redistribution) that can be specified with the **_protocol_.import** parameter. That parameter can be:

* A list of protocols to import
* A dictionary of protocols to import
* A dictionary with protocol-specific parameters. The only recognized parameter is **policy**, which specifies the import [routing policy](generic-routing-policies).

The **_protocol_.import** parameter can be specified:

* In a node definition to configure redistribution between routing protocol instances in the global routing table
* In a VRF definition to configure redistribution on all nodes using the specified VRF
* In a node VRF definition to configure in-VRF route redistribution on that node.

**Notes:**

* The **connected** keyword is used to specify connected routes; the **static** keyword specifies static routes configured with [**routing.static** data structure](generic-routing-static).
* The source protocol must be active on the node doing route import. For example, to import BGP routes into OSPF, both **bgp** and **ospf** configuration modules must be specified on the node.
* When importing IGP routes into another IGP within a VRF, the source IGP must have at least one parameter set in the VRF (to tell *netlab* the IGP is active within that VRF). You could, for example, set ***protocol*.active** to *True*
* The **routing** configuration module must be active on the node if you want to use **policy** parameter.
* The routing policy specified in the **policy** parameter must be specified in the global- or node **routing.policy** dictionary.

**Examples:**

Import BGP routes into OSPF:

```
nodes:
  r1:
    ospf.import: [ bgp ]
```

Import BGP and connected routes into OSPF (specified as a dictionary):

```
nodes:
  r1:
    ospf:
      import:
        bgp:
        connected:
```

Import BGP routes into OSPF using **i_bgp** routing policy:

```
nodes:
  r1:
    ospf.import.bgp.policy: i_bgp
```

One-way redistribution from RIP to OSPF within a VRF (note the **rip.active** VRF parameter that tells _netlab_ you want to have RIP active within that VRF):

```
vrfs:
  tenant:
    ospf.import: [ bgp, ripv2, connected ]
    ripv2.active: True
```
