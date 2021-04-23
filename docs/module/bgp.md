# BGP Configuration Module

This configuration module configures BGP routing process and BGP neighbors on Cisco IOS, Cisco Nexus-OS, Arista EOS and Junos.

Supported features:

* Multiple autonomous systems
* Direct (single-hop) EBGP sessions
* IBGP sessions between loopback interfaces
* BGP route reflectors
* Next-hop-self control on IBGP sessions
* Configurable link prefix advertisement
* Interaction with OSPF or IS-IS (IGP is disabled on external links)

You could use *global* or *per-node* parameters to configure BGP autonomous systems and route reflectors (you expected tons of nerd knobs in a BGP implementation, didn't you?):

* Using a global **as_list**, specify members and route reflectors in an autonomous system.
* Specify BGP AS and route reflector status of individual nodes with **bgp.as** and **bgp.rr** node parameters.

### Global BGP Configuration Parameters

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

#### Advanced Global Configuration Parameters

Advanced global configuration parameters include:

* **advertise_roles** -- list of link types and roles. Links matching any element of the list will be advertised into BGP. See *[Advertised BGP Prefixes](#advertised-bgp-prefixes)* for details.
* **ebgp_role** -- link role set on links connecting nodes from different autonomous systems. See *[Interaction with IGP](#interaction-with-igp)* for details.

### Node Configuration Parameters

Instead of using a global list of autonomous systems, you could specify a BGP autonomous system and route reflector role on individual nodes using these parameters:

* **bgp.as**: AS number -- specified on a node, or as default global value (propagated to all nodes without a specified AS number)
* **bgp.rr** -- the node is BGP route reflector within its autonomous system.
* **bgp.next_hop_self** -- use *next-hop-self* on IBGP sessions. This parameter can also be specified as a global value; system default is **true**.

Specifying a BGP autonomous system on individual nodes makes sense when each node uses a different BGP AS. See [EBGP leaf-and-spine fabric example](bgp_example/ebgp.md) for details.

**Notes:**
* **bgp.as** parameter *must* be specified for every node using BGP configuration module.
* The node AS number could be derived from the global **bgp.as_list**, from the default (global) value of **bgp.as** parameter, or specified on the node itself. Explore [simple BGP example](bgp_example/simple.md) to see how you can combine global AS number with node AS number.
* You could enable BGP configuration module globally using `module: [ bgp ]` as a top-level topology element, or for an individual node using `module: [ bgp ]` within node data. See [Segment Routing with BGP topology](https://github.com/ipspace/netsim-examples/blob/master/routing/sr-mpls-bgp/sr%2Bbgp.yml) for an example.

### Link-Level Parameters

You can also use these link-level parameters to influence the BGP prefix advertisements:

* **bgp.advertise** -- The link prefix will be configured with the **network** statement within the BGP process.

See [examples](#examples) for sample usage guidelines.

### Advertised BGP Prefixes

The following IP prefixes are configured with **network** statements within the BGP routing process:

* Loopback interface IPv4 prefix (usually a /32)
* IPv4 prefixes from links with **bgp.advertise** parameter set to **true**.
* Prefixes assigned to *stub* networks -- links with a single node attached to them or links with **role** set to **stub**. To prevent a stub prefix from being advertised, set **bgp.advertise** link parameter to **false**

**Notes:**
* If you set **bgp.advertise** parameter on a link, all nodes connected to the link advertise the link prefix. In the following example, the link prefix is advertised by PE1 and PE2.

```
links:
...
- pe1:
  pe2:
  bgp:
    advertise: true
``` 

* If you set **bgp.advertise** parameter within a node connected to a link, only that node advertises the link prefix. In the following example, the link prefix is advertised just by PE1:

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


### BGP Sessions

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

#### Notes on Unnumbered EBGP Sessions

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

### Interaction with IGP

BGP transformation module can set link *role* on links used for EBGP sessions. The link role (when not specified on the link itself) is set to the value of **defaults.bgp.ebgp_role** (default system value: **external**).

**Consequence:** default settings exclude links with EBGP sessions from IGP processes. See the [Simple BGP Example](bgp_example/simple.md) for details.

## Examples

```eval_rst
.. toctree::
   :maxdepth: 1

   bgp_example/simple.md
   bgp_example/ibgp.md
   bgp_example/ebgp.md
```
