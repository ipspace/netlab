# Common Routing Protocol Parameters

The following parameters are supported by most routing protocol modules:

* [Router ID](router_id)
* [Address families](af)
* [Passive interfaces](passive)
* [External interfaces](external)

(router_id)=
## Router ID

Router ID is configured with **router_id** node parameter (applies to all routing protocols) or with **_protocol_.router_id** node parameter (applies to the selected routing protocol). Router ID can be configured as an IPv4 address or as an integer.

Default **router_id** is taken from the IPv4 address of the loopback interface or from the [**router_id** address pool](../example/addressing-tutorial.md#using-built-in-address-pools) if there's no usable IPv4 address on the loopback interface.

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
* Node ID for R3 is 3 (the third node in the **nodes** dictionary). Router ID for R3 is taken from the loopback interface (10.0.0.3 unless you changed the **loopback** address pool) or from the **router_id** address pool (10.0.0.3).

(Af)=
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

* **R1**: IPv4 and IPv6. The configured list of addresses families overrides the topology defaults
* **R2**: IPv4 and IPv6. Node- and global parameters are dictionaries and can be merged.
* **R3**: IPv4 only. The **isis.af** parameter is fully specified within the node data, and explicitly disables IPv6 AF.
* **R4**: The **isis.af** parameter is set to an empty value, and is therefore calculated from the address families.
* **R5**: IPv6 only (global default)

(passive)=
## Passive Interfaces

An interface is configured as a *passive* interface (when supported by the routing protocol implementation) if:

* The link **type** is set to **stub**, or
* The link **role** is set to **stub** or **passive**, or
* **_protocol_.passive** parameter is set to True on a link or interface.

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
  role: stub
- r1:
  r2:
    ospf.passive: True
- r1:
  r2:
    ospf.passive: False
  role: stub
```

* The first link is a transit link
* The second link is a stub link (single node attached to the link) ⇨ passive interface on R1
* The third link has **stub** role ⇨ passive interfaces on R1 and R2
* The fourth link is a transit link, but the **ospf.passive** value is set on R2  interface ⇨ regular interface on R1, passive interface on R2
* The last link has **stub** role, but the **ospf.passive** value is set to *False* on R2 interface ⇨ passive interface on R1, regular interface on R2.

(external)=
## External Interfaces

Links with **role: external** are not included in the IGP routing processes. The  **external** role can be set with a link parameter or by the BGP module.

BGP module sets link role specified in **defaults.bgp.ebgp_role** on links connecting devices with different AS numbers. The system default value of that parameter is **external**, making inter-AS links excluded from the IGP processes.

If you want to include external subnets into your IGP (and disable BGP **next_hop_self** processing), set **defaults.bgp.ebgp_role** to **passive**.
