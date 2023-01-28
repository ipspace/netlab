# BGP Configuration Module

This configuration module configures BGP routing process and BGP neighbors on most [supported platforms](../platforms.md). The configuration module sets up BGP sessions according to these simple design rules:

* EBGP sessions are established between directly-connected IP addresses on every link where the connected routers belong to different autonomous systems. Parallel sessions are established for all address families (IPv4, IPv6) configured on the link.
* IBGP sessions are established between loopback interfaces of routers in the same autonomous system. Parallel sessions are established for all address families configured on the loopback interfaces.
* IGBP sessions could form a full mesh (when no router reflectors are configured in the autonomous system) or a hubs-and-spokes topology with a single route reflector cluster and a full mesh of IBGP sessions between route reflectors.
* Sessions (IBGP or EBGP) between directly-connected IP addresses are established whenever the real AS or the local AS of the devices differ, allowing you to build scenarios like IBGP-over-EBGP (EVPN design) or IBGP mesh across  multiple autonomous systems (ISP migration scenario).

More interesting BGP topologies can be created with [custom plugins](../plugins.md).

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Supported BGP Features

_netlab_ BGP configuration module supports these features:

* Multiple autonomous systems
* IPv4 and IPv6 address families
* Direct (single-hop) EBGP sessions
* IBGP sessions between loopback interfaces
* EBGP sessions between auto-generated IPv6 link-local addresses
* RFC8950-style IPv4 address family on EBGP IPv6 LLA sessions
* BGP route reflectors
* Next-hop-self control on IBGP sessions
* BGP community propagation
* Configurable activation of default address families
* Configurable link prefix advertisement
* Additional (dummy) IPv4 prefix advertisement
* Changing local autonomous system for individual BGP sessions (*local-as*)
* Static **router-id** and **cluster-id**
* Interaction with OSPF or IS-IS (IGP is disabled on external links)

## Platform Support

[Platforms supporting BGP configuration module](platform-routing-support) support most of the functionality mentioned above with the following exceptions:

* Cumulus Linux 5.2.0 using NVUE cannot configure IBGP sessions between loopback interfaces. Please [see caveats for more details](caveats-cumulus-nvue).

The following features are only supported on a subset of platforms:

| Operating system      | IPv6 LLA<br />EBGP sessions | Unnumbered IPv4<br />EBGP sessions | EBGP<br>local AS | IBGP<br>local AS | Configurable<br>default AF |
| --------------------- | :-: | :-: | :-: | :-: | :-: |
| Arista EOS            |  ❌  |  ❌  |  ✅ |  ✅ |  ✅ |
| Cisco IOS/IOS XE      |  ❌  |  ❌  |  ✅ |  ✅ |  ✅ |
| Cisco IOS XRv         |  ❌  |  ❌  |  ❌  |  ❌  |  ✅ |
| Cumulus Linux 4.x     |  ✅ |  ✅ |  ✅ |  ✅ |  ✅ |
| Cumulus Linux 5.x     |  ✅ |  ✅ |  ❌  |  ❌  |  ✅ |
| Dell OS10             |  ✅  |  ✅  |  ✅ |  ❌  |  ✅  |
| FRR 7.5.0             |  ✅ |  ❌  |  ✅  |  ✅  |  ✅ |
| Nokia SR Linux        |  ✅ |  ❌ |  ✅ |  ✅  |  ✅  |
| Nokia SR OS           |  ❌ |  ❌ |  ✅ |  ✅  |  ✅  |
| VyOS                  |  ✅  |  ✅  |  ✅ |  ❌  |  ✅  |

## Global BGP Configuration Parameters

You could use *global* or *per-node* parameters to configure BGP autonomous systems and route reflectors:

* Specify BGP AS and route reflector status of individual nodes with **bgp.as** and **bgp.rr** node parameters.
* Using a global **as_list**, specify members and route reflectors in multiple autonomous systems in your lab.

The simplest way to build a network with a single BGP autonomous system is to specify the BGP AS number in global **bgp.as** parameter and the list of route reflectors in the global **bgp.rr_list** parameter (See [IBGP-over-OSPF Data Center Fabric example](bgp_example/ibgp.md) for details):

```
bgp:
  as: 65000
  rr_list: [ s1, s2 ]
```

When building a more complex lab with multiple autonomous systems, you might want to use **bgp.as_list** global parameter to specify a dictionary of autonomous systems (although you could still set BGP AS numbers and RR status with node attributes). Every autonomous system in the **bgp.as_list** should have two elements:

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

## Advanced Global Configuration Parameters

Advanced global configuration parameters include:

* **bgp.community** -- configure BGP community propagation. By defaults, standard and extended communities are propagated to IBGP neighbors, and standard communities are propagated to EBGP neighbors. See *[BGP Community Propagation](#bgp-communities-propagation)* for more details.
* **bgp.advertise_roles** -- list of link types and roles. Links matching any element of the list will be advertised into BGP. See *[Advertised BGP Prefixes](#advertised-bgp-prefixes)* for details.
* **bgp.ebgp_role** -- link role set on links connecting nodes from different autonomous systems. See *[Interaction with IGP](#interaction-with-igp)* for details.
* **bgp.advertise_loopback** -- when set to `True` (default), the loopback IP addresses of the default loopback interface and any other [loopback links](links-loopback) are advertised as a BGP prefix. Set it to `False` in global defaults or as a node setting to disable loopback prefix advertisements.

## Node Configuration Parameters

Instead of using a global list of autonomous systems, you could specify a BGP autonomous system and route reflector role on individual nodes using these parameters:

* **bgp.as**: AS number -- specified on a node, or as default global value (propagated to all nodes without a specified AS number)
* **bgp.rr** -- the node is BGP route reflector within its autonomous system.

```{note}
* **bgp.as** parameter *must* be specified for every node using BGP configuration module.
* The node AS number could be derived from the global **bgp.as_list**, from the default (global) value of **bgp.as** parameter, or specified on the node itself. Explore [simple BGP example](bgp_example/simple.md) to see how you can combine global AS number with node AS number.
* Specifying a BGP autonomous system on individual nodes makes sense when each node uses a different BGP AS. See [EBGP leaf-and-spine fabric example](bgp_example/ebgp.md) for details.
```

Additional per-node BGP configuration parameters include:

* **bgp.advertise_loopback** -- when set to `False`, the IP prefixes configured on loopback interfaces are not advertised in BGP. See also [*Advanced Global Configuration Parameters*](#advanced-global-configuration-parameters).
* **bgp.community** -- override global BGP community propagation defaults for this node. See *[BGP Community Propagation](#bgp-communities-propagation)* for more details.
* **bgp.local_as** -- the autonomous system to use on all EBGP sessions.
* **bgp.next_hop_self** -- use *next-hop-self* on IBGP sessions. This parameter can also be specified as a global value; system default is **true**.
* **bgp.originate** -- a list of additional prefixes to advertise. The advertised prefixes are supported with a static route pointing to *Null0*.
* **bgp.router_id** -- set static router ID. Default **router_id** is taken from the IPv4 address of the loopback interface or from the **router_id** address pool if there's no usable IPv4 address on the loopback interface.

(bgp-advanced-node)=
Finally, BGP configuration module supports these advanced node parameters that you probably shouldn't touch without a very good reason:

* **bgp.rr_cluster_id** -- set static route reflector cluster ID. The default value is the lowest router ID of all route reflectors within the autonomous system.
* **bgp.replace_global_as** (default: True) -- the default implementation of **neighbor local-as** command replaces the real autonomous system (**bgp.as**) with the *local* autonomous system. Set this parameter to *false* to disable that functionality and include both autonomous systems in the AS path[^RAS_P].
* **bgp.sessions** (node or global parameter) -- specifies which transport sessions (IPv4 and/or IPv6) should be created for each BGP session type (IBGP, EBGP, or IBGP created through *local-as*)[^SESS_DM]. See *[bgp-sessions](https://github.com/ipspace/netlab/blob/dev/tests/topology/input/bgp-sessions.yml)* test case for an example.
* **bgp.activate** (node or global parameter) -- specifies which default address families (IPv4 AF on IPv4 session, IPv6 on IPv6 session) should be created for each BGP session type (IBGP, EBGP, or IBGP created through *local-as*)[^ACT_CFG]. See *[leaf-spine](https://github.com/ipspace/netlab/blob/dev/tests/integration/bgp/local-as/leaf-spine.yml)* local AS test case for an example.

[^SESS_DM]: This parameter influences the data structures built during the data transformation phase and is thus available on all platforms supporting BGP configuration module.

[^ACT_CFG]: This parameter has to be supported by the device configuration templates and is thus not available on all platforms.

[^RAS_P]: This functionality might not be configurable on all platforms. For example, Arista EOS supports only the **neighbor local-as no-prepend replace-as** command.

## VRF Parameters

You can set a VRF-specific BGP router ID with **bgp.router_id** VRF parameter. Use this setting when building topologies with back-to-back links between VRFs on the same device.

BGP is always enabled for all VRF address families. The connected interfaces (and OSPF routes when applicable) are always redistributed into the BGP routing process. 

To stop the creation of VRF EBGP sessions, set **bgp** VRF parameter to *False* (see also [](routing_disable_vrf)).

## Link-Level Parameters

You can also use these link-level parameters to influence the BGP prefix advertisements:

* **bgp.advertise** -- The link prefix will be configured with the **network** statement within the BGP process.

You can also [disable all EBGP sessions on a link](routing_disable).

See [examples](#more-examples) for sample usage guidelines.

## Interface-Level Parameters

You can specify **bgp.local_as** for individual node-to-link attachments, for example:

```
links:
- r1:
    bgp.local_as: 65100
  r2:
    bgp.local_as: 65101
```

You can also [disable all EBGP sessions on an interface](routing_disable).

## Advertised BGP Prefixes

The following IPv4/IPv6 prefixes are configured with **network** statements within the BGP routing process:

* IPv4/IPv6 prefixes configured on the default loopback interface and [loopback links](links-loopback) unless the **bgp.advertise_loopback** is set to `False`.
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

### Using bgp.originate Node Attribute

If you set **bgp.originate** parameter on a node, the node will advertise the prefix in to BGP via a network statement, and create a static route for the prefix with a nexthop set to *Null0*.

```
nodes:
...
  pe1:
    module: [bgp]
    bgp:
      originate:
        - "172.16.0.0/19"
```

## BGP Sessions

The BGP transformation module builds a list of BGP neighbors for ever node. That list of neighbors is then used to configure BGP neighbors within the BGP routing process:

**IBGP sessions**
* If there are no route reflectors within an autonomous system (no device within the autonomous system has **bgp.rr** set to *true*), you'll get a full mesh of IBGP sessions.
* Router reflectors have IBGP sessions to all other nodes in the same AS. When the remote node is not a router reflector, *route-reflector-client* is configured on the IBGP session.
* Route reflector clients have IBGP sessions with route reflectors (nodes within the same AS with **bgp.rr** set).
* IBGP sessions are established between loopback interfaces. You should combine IBGP deployment with an IGP configuration module like [OSPF](ospf.md).
* Parallel IBGP sessions are established for all IP address families configured on loopback interfaces[^BSESS]. See also [IPv6 support](#ipv6-support).

[^BSESS]: If allowed by the **bgp.sessions** parameter

See the [IBGP Data Center Fabric](bgp_example/ibgp.md) example for more details.

**EBGP sessions**
* Whenever multiple nodes connected to the same link use different AS numbers, you'll get a full mesh of EBGP sessions between them.
* Global (**bgp.as**) and local (**bgp.local_as**) autonomous systems are considered when deciding to create a session between two adjacent nodes, allowing you to create EBGP sessions between nodes belonging to the same AS, or IBGP sessions between nodes belonging to different AS.
* Parallel EBGP sessions are established for all IP address families configured on the link[^BSESS]. See also [IPv6 support](#ipv6-support).

See the [Simple BGP Example](bgp_example/simple.md) and [EBGP Data Center Fabric](bgp_example/ebgp.md) example for more details.

### Notes on Unnumbered EBGP Sessions

Unnumbered EBGP sessions are supported on a few platforms. *netlab* creates an IPv6 LLA EBGP session when the **unnumbered** link- or interface attribute is set, or when **ipv6** interface address or link prefix is set to *True* (IPv6 LLA).

*netlab* can use an IPv6 LLA EBGP session to transport IPv4 address family with IPv6 next hops (RFC 8950) -- the functionality commonly used to implement *unnumbered EBGP sessions*. *netlab* will enable IPv4 AF over IPv6 LLA EBGP session when the **unnumbered** link- or interface attribute is set, or when **ipv4** interface address or link prefix is set to *True*.

## IPv6 Support

All BGP configuration templates include IPv4 and IPv6 address family configuration. Both address families are treated identically, allowing you to build IPv4-only, IPv6-only, or dual-stack networks:

* An address family (IPv4 or IPv6) is enabled within the BGP routing process as soon as the device has at least one interface with an address from that address family.
* BGP configuration uses separate BGP sessions for IPv4 and IPv6 address families[^BSESS]. Create your own configuration templates to enable IPv6 AF over IPv4 BGP sessions or IPv4 AF over IPv6 BGP sessions.
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

## Related Plugins

```eval_rst
.. toctree::
   :maxdepth: 1

   ../plugins/ebgp.utils.md
```

## More Examples

```eval_rst
.. toctree::
   :maxdepth: 1

   bgp_example/simple.md
   bgp_example/ibgp.md
   bgp_example/ebgp.md
```
