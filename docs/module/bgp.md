# BGP Configuration Module

This configuration module configures BGP routing process and BGP neighbors on Cisco IOS, Cisco Nexus-OS, Arista EOS and Junos.

Supported features:

* Multiple autonomous systems
* Direct (single-hop) EBGP sessions
* IBGP sessions between loopback interfaces
* BGP route reflectors
* Next-hop-self control on IBGP sessions
* BGP community propagation
* IPv4 and IPv6 address families
* Configurable link prefix advertisement
* Additional (dummy) prefix advertisement
* Interaction with OSPF or IS-IS (IGP is disabled on external links)

You could use *global* or *per-node* parameters to configure BGP autonomous systems and route reflectors (you expected tons of nerd knobs in a BGP implementation, didn't you?):

* Using a global **as_list**, specify members and route reflectors in an autonomous system.
* Specify BGP AS and route reflector status of individual nodes with **bgp.as** and **bgp.rr** node parameters.

## Global BGP Configuration Parameters

Use **bgp.as_list** global parameter to specify a dictionary of autonomous systems. Every autonomous system should have two elements:

* **members** -- list of nodes within the autonomous system
* **rr** -- list of route reflectors within the autonomous system.

For example, use the following configuration to build a core network connected to two external autonomous systems:

```
bgp:
  as_list:
    65000:
      members: [ rr1, rr2, pe1, pe2 ]
      rr: [ rr1, rr2 ]
    65001:
      members: [ e1 ]
    65002:
      members: [ e2 ]
``` 

When you're building a network with a single BGP autonomous system, it might be simpler to specify the default value of BGP AS number in **bgp.as** parameter instead of listing all nodes within that autonomous system. When using this approach, specify the list of route reflectors in **bgp.rr_list** parameter.

```
bgp:
  as: 65000
  rr_list: [ s1, s2 ]
```

See [IBGP-over-OSPF Data Center Fabric example](bgp_example/ibgp.md) for details.

## Advanced Global Configuration Parameters

Advanced global configuration parameters include:

* **community** -- configure BGP community propagation. By defaults, standard and extended communities are propagated to IBGP neighbors, and standard communities are propagated to EBGP neighbors. See *[BGP Community Propagation](#bgp-communities-propagation)* for more details.
* **advertise_roles** -- list of link types and roles. Links matching any element of the list will be advertised into BGP. See *[Advertised BGP Prefixes](#advertised-bgp-prefixes)* for details.
* **ebgp_role** -- link role set on links connecting nodes from different autonomous systems. See *[Interaction with IGP](#interaction-with-igp)* for details.
* **advertise_loopback** -- when set to `True` (default), the loopback IP address is advertised as a BGP prefix. Set it to `False` in global defaults or as a node setting to disable loopback prefix advertisements.

## Node Configuration Parameters

Instead of using a global list of autonomous systems, you could specify a BGP autonomous system and route reflector role on individual nodes using these parameters:

* **bgp.as**: AS number -- specified on a node, or as default global value (propagated to all nodes without a specified AS number)
* **bgp.rr** -- the node is BGP route reflector within its autonomous system.
* **bgp.next_hop_self** -- use *next-hop-self* on IBGP sessions. This parameter can also be specified as a global value; system default is **true**.

Specifying a BGP autonomous system on individual nodes makes sense when each node uses a different BGP AS. See [EBGP leaf-and-spine fabric example](bgp_example/ebgp.md) for details.

Additional per-node BGP configuration parameters include:

* **bgp.advertise_loopback** -- when set to `False`, the loopback IP prefix is not advertised in BGP. See also [*Advanced Global Configuration Parameters*](#advanced-global-configuration-parameters).
* **bgp.originate** -- a list of additional prefixes to advertise. The advertised prefixes are supported with a static route pointing to *Null0*.
* **bgp.community** -- override global BGP community propagation defaults for this node. See *[BGP Community Propagation](#bgp-communities-propagation)* for more details.

**Notes:**
* **bgp.as** parameter *must* be specified for every node using BGP configuration module.
* The node AS number could be derived from the global **bgp.as_list**, from the default (global) value of **bgp.as** parameter, or specified on the node itself. Explore [simple BGP example](bgp_example/simple.md) to see how you can combine global AS number with node AS number.
* You could enable BGP configuration module globally using `module: [ bgp ]` as a top-level topology element, or for an individual node using `module: [ bgp ]` within node data. See [Segment Routing with BGP topology](https://github.com/ipspace/netsim-examples/blob/master/routing/sr-mpls-bgp/sr%2Bbgp.yml) for an example.

## Link-Level Parameters

You can also use these link-level parameters to influence the BGP prefix advertisements:

* **bgp.advertise** -- The link prefix will be configured with the **network** statement within the BGP process.

See [examples](#more-examples) for sample usage guidelines.

## Advertised BGP Prefixes

The following IPv4/IPv6 prefixes are configured with **network** statements within the BGP routing process:

* Loopback interface IPv4/IPv6 prefix unless the **bgp.advertise_loopback** is set to `False`.
* IPv4/IPv6 prefixes from links with **bgp.advertise** parameter set to **true**.
* Prefixes assigned to *stub* networks -- links with a single node attached to them or links with **role** set to **stub**. To prevent a stub prefix from being advertised, set **bgp.advertise** link parameter to **false**
* IPv4 prefixes in **bgp.originate** list. Static routes to *Null0* are created for those prefixes if needed.

### Using bgp.advertise Link Attribute

* If you set **bgp.advertise** parameter on a link, all nodes connected to the link advertise the link prefix. In the following example, PE1 and PE2 advertise the link prefix.

```
links:
...
- pe1:
  pe2:
  bgp:
    advertise: true
``` 

* If you set **bgp.advertise** parameter within a node connected to a link, only that node advertises the link prefix. In the following example, only PE1 advertises the link prefix:

```
links:
...
- pe1:
    bgp:
      advertise: true
  pe2:
``` 

* You can change the default prefix advertisement rules with the  **defaults.bgp.advertise_roles** list. The system default value of that variable is **[ stub ]**. For example, to advertise LAN (multi-access) and stub prefixes, use the following setting:

```
defaults:
  bgp:
    advertise_roles: [ lan, stub ]
``` 


## BGP Sessions

The BGP transformation module builds a list of BGP neighbors for ever node. That list of neighbors is then used to configure BGP neighbors within the BGP routing process:

**IBGP sessions**
* If there are no route reflectors within an autonomous system (no device within the autonomous system has **bgp.rr** set to *true*), you'll get a full mesh of IBGP sessions.
* Router reflectors have IBGP sessions to all other nodes in the same AS. When the remote node is not a router reflector, *route-reflector-client* is configured on the IBGP session.
* Route reflector clients have IBGP sessions with route reflectors (nodes within the same AS with **bgp.rr** set).
* IBGP sessions are established between loopback interfaces. You should combine IGBP deployment with an IGP configuration module like [OSPF](ospf.md).

See the [IBGP Data Center Fabric](bgp_example/ibgp.md) example for more details.

**EBGP sessions**
* Whenever multiple nodes connected to the same link use different AS numbers, you'll get a full mesh of EBGP sessions between them.

See the [Simple BGP Example](bgp_example/simple.md) and [EBGP Data Center Fabric](bgp_example/ebgp.md) example for more details.

### Notes on Unnumbered EBGP Sessions

Unnumbered EBGP sessions are supported by the data model, but not by configuration templates. The transformed data model includes **unnumbered** and **ifindex** elements on EBGP neighbors reachable over unnumbered interfaces -- compare a regular EBGP neighbor (L2) with an unnumbered EBGP neighbor (L1):

```
- bgp:
    as: 65001
    neighbors:
    - as: 65100
      ifindex: 1
      name: l1
      type: ebgp
      unnumbered: true
    - as: 65101
      ipv4: 172.16.0.1
      name: l2
      type: ebgp
```

The transformed data model gives you enough information to create Cumulus-style BGP neighbor statements.

## IPv6 Support

All BGP configuration templates include IPv4 and IPv6 address family configuration. Both address families are treated identically, allowing you to build IPv4-only, IPv6-only, or dual-stack networks:

* An address family (IPv4 or IPv6) is enabled within the BGP routing process as soon as the device has at least one interface with an address from that address family.
* BGP configuration uses separate BGP sessions for IPv4 and IPv6 address families. Create your own configuration templates to enable IPv6 AF over IPv4 BGP sessions or IPv4 AF over IPv6 BGP sessions.
* Whenever an IBGP neighbor has an IPv4/IPv6 address on its loopback interface, an IBGP sessions is configured between the IPv4/IPv6 addresses, and the IPv4/IPv6 address family is enabled for that session.
* An EBGP IPv4/IPv6 session is configured whenever a directly-connected router in another AS has an IPv4/IPv6 address on the directly-connected link.

No additional checks are performed regarding the viability of IPv4 or IPv6 BGP sessions. For example:

* You could configure IPv6 addresses on loopback interfaces, but not on P2P links. The IPv6 IBGP sessions will be configured, but won't work.
* You could configure IPv4 and IPv6 addresses throughout the network, but use OSPFv2 as the routing protocol. EBGP IPv6 sessions will work, IBGP IPv6 sessions won't.
* You could configure addresses on individual nodes connected to an inter-AS link. If you configure IPv6 addresses on some nodes but not others, the system might configure useless EBGP sessions.

## Interaction with IGP

BGP transformation module can set link *role* on links used for EBGP sessions. The link role (when not specified on the link itself) is set to the value of **defaults.bgp.ebgp_role** (default system value: **external**).

**Consequence:** default settings exclude links with EBGP sessions from IGP processes. See the [Simple BGP Example](bgp_example/simple.md) for details.

## BGP Communities Propagation

The propagation of BGP communities over IBGP and EBGP sessions is controlled with global- or node-level **bgp.community** attribute.

The value of **bgp.community** attribute could be:

* A string: **standard** or **extended** -- only specified communities will be propagated to IBGP and EBGP neighbors. In the following example, R1 propagates standard communities to all its neighbors.

```
nodes:
  r1:
    bgp:
      community: standard
```

* A list of strings (**standard** and/or **extended**) -- all communities specified in the list will be propagated to IBGP and EBGP neighbors. Most network operating systems will be configured with **both** configuration keyword if you specify `['standard','extended']` as the value. In the following example, R1 propagates standard and extended communities to all its neighbors.

```
nodes:
  r1:
    bgp:
      community: [standard, extended]
```

* A dictionary with two keys: **ibgp** and **ebgp**. The value of each key could be a string or a list (see above). The following example sets a network-wide default -- send standard and extended communities to IBGP neighbors, and standard communities to EBGP neighbors (this is the global default set in global **topology-defaults.yml** file).

```
bgp:
  community: 
    ibgp: [standard, extended]
    ebgp: [standard]
```

* To override global defaults and stop community propagation, use an empty list as the **bgp.community** value. In the following example, R1 will not send any BGP communities to its BGP peers.

```
nodes:
  r1:
    bgp:
      community: []
```

## More Examples

```eval_rst
.. toctree::
   :maxdepth: 1

   bgp_example/simple.md
   bgp_example/ibgp.md
   bgp_example/ebgp.md
```
