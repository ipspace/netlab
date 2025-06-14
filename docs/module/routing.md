(generic-routing)=
# Generic Routing Configuration Module

This configuration module implements generic routing features:

* [Routing policies (route maps)](generic-routing-policies)
* [Prefix filters (prefix-lists)](generic-routing-prefixes)
* [BGP AS-path filters](generic-routing-aspath)
* [BGP community filters](generic-routing-community)
* [Static routes](generic-routing-static)

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(generic-routing-platforms)=
## Platform Support

The following table describes high-level per-platform support of generic routing features:

| Operating system      | Routing<br>policies | Prefix<br>filters| AS-path<br>filters | BGP<br>communities | Static<br>routes|
| ------------------ |:--:|:--:|:--:|:--:|:--:|
| Arista EOS         | ✅ | ✅ | ✅ | ✅ | ✅ |
| Aruba AOS-CX       | ✅ | ✅ | ✅ | ✅ |
| Cisco IOS/XE[^18v] | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cumulus Linux      | ✅ | ✅ | ✅ | ✅ | ✅ |
| Dell OS10          | ✅ | ✅ | ✅ | ✅ | ✅ |
| FRR                | ✅ | ✅ | ✅ | ✅ | ✅ |
| Linux              | ❌  | ❌  | ❌  | ❌  | ✅ |
| Junos              | ✅ | ✅ | ✅ | ✅ | ✅ |
| Nokia SR Linux     |  ✅ |  ✅ [❗](caveats-srlinux) |
| Nokia SR OS        |  ✅ |
| VyOS               |  ✅ |  ✅ | ✅ |  ✅  |

```{tip}
See [Routing Integration Tests Results](https://release.netlab.tools/_html/coverage.routing) for more details.
```

[^18v]: Includes Cisco IOSv, Cisco IOSvL2, Cisco CSR 1000v, Cisco Catalyst 8000v, Cisco IOS-on-Linux (IOL), and IOL Layer-2 image.

(generic-routing-policies)=
## Routing Policies

Routing policies are lists of instructions that can **match** route parameters and **set** route attributes. Each routing policy entry can have these attributes:

* **action**: A routing policy entry can **permit** or **deny** matched routes (default: **permit**)
* **sequence**: Statement sequence number. When not specified, *netlab* sets a routing policy entry's **sequence** number to ten times its list position.
* **match**: Conditions that must match for the routing policy entry to take effect. Entries without a **match** parameter match all routes
* **set**: Parameters that are set on matched routes.

You can match these route parameters in a _netlab_ routing policy:

* **prefix**: Match a [prefix filter](generic-routing-prefixes) defined in **routing.prefix** dictionary
* **aspath**: Match a [BGP AS-path filter](generic-routing-aspath) defined in **routing.aspath** dictionary
* **community**: Match a BGP [community filter](generic-routing-community) defined in **routing.community** dictionary

You can set these route parameters in a _netlab_ routing policy:

* **locpref**: BGP local preference
* **med**: Route metric (for example, BGP MED)
* **prepend**: BGP AS-path prepending ([more details](plugin-bgp-policy-attributes))
* **weight**: BGP weight
* **community**: A dictionary that can be used to set, add, or remove standard, large, or extended communities.

The **set.community** dictionary has these parameters:

* **standard**: Standard BGP communities to set
* **large**: Large BGP communities to set
* **extended**: Extended BGP communities to set. The value is passed to the network device as-is (the same value might not work on all devices).
* **append**: Add communities to existing BGP communities
* **delete**: Remove specified communities from the BGP route
* **delete_list**: Remove communities matching the specified community list from the BGP route. Cannot be used with any other **set.community** parameters.

Routing policies are specified in the global- or node-level **routing.policy** dictionary (see [](routing-object-import) and  [](routing-object-merge) for more details).

The dictionary keys in the **routing.policy** dictionary are policy names (route map names), and the dictionary values are routing policies (lists of routing policy entries).

The following example specifies three routing policies: two global routing policies setting BGP local preference to different values and a node routing policy setting MED.

```
module: [ routing ]

routing.policy:
  lp_17:
  - set.locpref: 17
  lp_42:
  - set.locpref: 42

nodes:
  r1:
    routing.policy:
      set_med:
      - set.med: 100
```

### Platform Support

You can use these routing policy **match** parameters on devices supported by the **routing** module:

| Operating system    | IPv4/IPv6<br>prefix | IPv4/IPv6<br>next hop | BGP<br>AS-path | BGP<br>Community |
|---------------------|:--:|:--:|:--:|:--:|
| Arista EOS          | ✅ | ❌  | ✅ | ✅ |
| Aruba AOS-CX        | ✅ | ❌  | ✅ | ✅ |
| Cisco IOS/XE[^18v]  | ✅ | ❌  | ✅ | ✅ |
| Cumulus Linux       | ✅ | ❌  | ✅ | ✅ |
| Dell OS10           | ✅ | ❌  | ✅ | ✅ |
| Junos               | ✅ | ❌  | [✅](caveats-junos) | ✅ |
| FRR                 | ✅ | ❌  | ✅ | ✅ |
| Nokia SR Linux      | ✅ |
| VyOS                | ✅ | ❌  | ✅ | ✅ |

You can use these routing policy **set** parameters on devices supported by the **routing** module:

| Operating system    | AS-path<br>prepend | Local<br>preference | MED | Weight | Community |
|---------------------|:--:|:--:|:--:|:--:| :--:|
| Arista EOS          | ✅ | ✅ | ✅ | ✅ | ✅ |
| Aruba AOS-CX        | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cisco IOS/XE[^18v]  | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cumulus Linux       | ✅ | ✅ | ✅ | ✅ | ✅ |
| Dell OS10           | ✅ | ✅ | ✅ | ✅ | ✅ |
| Junos               | ✅ | ✅ | ✅ | ❌  | ✅ |
| FRR                 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Nokia SR Linux      | ❌  | ✅ | ✅ | ❌  | ❌  |
| Nokia SR OS         | ❌  | ✅ | ✅ | ❌  | ❌  |
| VyOS                | ✅ | ✅ | ✅ | ❌  | ✅ |

The **set.community** attribute can be used to set these BGP communities on supported devices:

| Operating system    | Standard<br>community | Large<br>community | Extended<br>community |
|---------------------|:--:|:--:|:--:|
| Arista EOS          | ✅ | ✅ | ✅ |
| Aruba AOS-CX        | ✅ | ❌  | ❌  |
| Cisco IOS/XE[^18v]  | ✅ | ❌  | ❌  |
| Cumulus Linux       | ✅ | ✅ | ✅ |
| Dell OS10           | ✅ | ❌ | ✅ |
| Junos               | ✅ | ✅ | ✅ |
| FRR                 | ✅ | ✅ | ✅ |
| VyOS                | ✅ | ✅ | ✅ |

Apart from setting BGP communities on BGP routes, these devices can execute additional operations on BGP communities:

| Operating system    | Append | Delete | Delete list |
|---------------------|:--:|:--:| :--:|
| Arista EOS          | ✅ | ✅ | ✅ |
| Aruba AOS-CX        | ✅ | ✅ | ❌  |
| Cisco IOS/XE[^18v]  | ✅ | ✅❗️| ✅ |
| Cumulus Linux       | ✅ | ❌  | ❌  |
| Dell OS10           | ✅ | ❌  | ❌  |
| Junos               | ✅ | ✅ | ❌  |
| FRR                 | ✅ | ✅❗️ | ✅ |
| VyOS                | ✅ | ❌  | ❌  |

**Notes:**
* _netlab_ is creating an internal BGP community list on FRR and Cisco IOS/XE to delete BGP communities specified with the **set.community.delete** routing policy parameter. This approach is currently limited to standard BGP communities.

### Shortcut Routing Policy Definitions

Routing policies tend to be verbose. You have to define *a list of* dictionaries with *set* and *match* attributes. *netlab* tries to reduce the verbosity with two shortcuts:

* A routing policy with a single entry does not have to be a one-element list but could be a dictionary. For example, the following two routing policies are equivalent:

```
routing.policy:
  p1:
  - set.locpref: 100
  p2:
    set.locpref: 100
```

* Unambiguous keywords like **med** and **locpref** do not need to be within the **set** or **match** dictionary. *netlab* automatically moves them into the routing-policy-entry **set** dictionary. For example, the following two routing policies are equivalent:

```
routing.policy:
  p1:
  - set.locpref: 100
    match.prefix: pfx-list
  p2:
    locpref: 100
    prefix: pfx-list
```

(routing-policy-ds)=
### Dual-Stack Routing Policies

Most network operating systems cannot use **match ip** and **match ipv6** commands in the same route map entry and behave differently when testing an IPv6 route with a route map entry that contains only **match ip**.

To avoid inconsistencies, _netlab_ usually generates a separate per-address-family *route map* for each routing policy configured on a network device. The address-family-specific route maps are then used in device configuration.

For example:

* If you create a routing policy **X**, and a node runs IPv4 and IPv6, _netlab_ configures two route maps: **X-ipv4** and **X-ipv6**.
* When the same routing policy is used on a node that runs only IPv4, _netlab_ configures only **X-ipv4**.
* When the routing policy **X** is used in **bgp.policy** attribute, _netlab_ uses route map **X-ipv4** for IPv4 EBGP sessions and **X-ipv6** for IPv6 EBGP sessions.

(generic-routing-prefixes)=
## Prefix Filters (prefix-lists)

Prefix filters are lists of conditions (usually known as *lists*) that permit or deny IPv4 or IPv6 prefixes. You can use prefix filters in the **match.prefix** and **match.nexthop** parameters of routing policies to match IPv4/IPv6 routes or next hops. Each prefix filter entry can have these attributes:

* **action**: A prefix filter entry can **permit** or **deny** matched prefixes (default: **permit**)
* **sequence**: Statement sequence number. When not specified, *netlab* sets a prefix filter entry's **sequence** number to ten times its list position.
* **ipv4**: IPv4 prefix to match
* **ipv6**: IPv6 prefix to match
* **pool**: Name of the addressing pool to match
* **prefix**: [A named prefix](named-prefixes) to match
* **min**: Minimum prefix length. It could be specified as an integer or a dictionary with **ipv4** and **ipv6** keys.
* **max**: Maximum prefix length in the same format as the **min** parameters.

Prefix filters are specified in the global- or node-level **routing.prefix** dictionary (see [](routing-object-import) and  [](routing-object-merge) for more details). 

The keys of the **routing.prefix** dictionary are filter names (prefix-list names), and the values are prefix filters (lists of prefix filter entries).

The following example specifies a prefix filter that matches the loopback pool, a named prefix, and an IPv6 prefix:

```
module: [ routing ]

prefix:
  lb_c1: 192.168.42.0/24

routing.prefix:
  loopbacks:
  - pool: loopback
  - prefix: lb_c1
  - ipv6: 2001:db8:cafe:2::/64
```

(routing-prefix-ds)=
### Dual-Stack Prefix Lists

Address pools, named prefixes, and prefix filter entries can contain IPv4 and IPv6 prefixes. Meanwhile, most network operating systems use different configuration objects to match IPv4 and IPv6 prefixes.

_netlab_ generates separate per-address-family *prefix lists* for every prefix filter configured on a network device. The address family is appended to the prefix list name to deal with devices that cannot use the same names for IPv4 and IPv6 prefix lists.

To avoid route map inconsistencies, a prefix list that contains no usable entries (for example, an IPv6 prefix list generated from a prefix filter that matches only IPv4 prefixes) has a single *deny everything* condition.

Let's assume we're using the following prefix filters:

```
routing.prefix:
  p1:
    - ipv4: 192.168.24.0/24
    - ipv6: 2001:db8:0:1::/64
  p2:
    - ipv4: 172.16.0.0/16
```

_netlab_ generates these prefix lists on an IPv4-only device (IPv6 prefix list is not generated, and entry #20 is missing from P1):

```
ip prefix-list p1-ipv4 seq 10 permit 192.168.24.0/24
!
ip prefix-list p2-ipv4 seq 10 permit 172.16.0.0/16
```

Meanwhile, the following prefix lists are generated on a dual-stack device (including a meaningless IPv6 prefix list P2)

```
ip prefix-list p1-ipv4 seq 10 permit 192.168.24.0/24
!
ip prefix-list p2-ipv4 seq 10 permit 172.16.0.0/16
!
ipv6 prefix-list p1-ipv6 seq 20 permit 2001:db8:0:1::/64
!
ipv6 prefix-list p2-ipv6 seq 10 deny ::/0
```

(generic-routing-aspath)=
## BGP AS-Path Filters

AS-path filters are lists of conditions (usually known as *as-path access lists*) that permit or deny BGP AS paths (and consequently the routes carrying them). They match a list of AS numbers or a regular expression. You can use them in the **match.aspath** parameters of routing policies to match BGP routes. Each AS-path filter entry can have these attributes:

* **action**: A prefix filter entry can **permit** or **deny** matched prefixes (default: **permit**)
* **sequence**: Statement sequence number. When not specified, *netlab* sets a prefix filter entry's **sequence** number to ten times its list position.
* **path**: A list of autonomous systems to match or a regular expression to match

AS-path filters are specified in the global- or node-level **routing.aspath** dictionary (see [](routing-object-import) and  [](routing-object-merge) for more details).

The keys of the **routing.aspath** dictionary are filter names (prefix-list names), and the values are AS-path filters (lists of AS-path filter entries).

The following example specifies an AS-path access list that drops BGP prefixes originated in AS 65000 and permits everything else:

```
module: [ routing ]

routing.aspath:
  not_65000:
  - action: deny
    path: _65000$
  - action: permit
```

### Shortcut BGP AS-Path Definitions

Filters encoded in YAML tend to be verbose, and we tried to do as much as we could to reduce BGP AS-path filter verbosity:

* You can skip the **action** and **sequence** attributes.
* Each entry in a BGP AS-path filter could be a simple string or a list of AS numbers. Such entries are converted into dictionaries with the **path** element set to the entry's value.
* A list of AS numbers in the **path** element is converted into a string of AS numbers separated by a blank
* A BGP AS-path filter could be a single string. That string is first converted into a list and subsequently into a list containing a single dictionary.

The following example lists various shortened definitions of BGP AS-path filters:

```
routing:
  aspath:
    ap1: 65000                      # AS-path ACL as int => single-entry ACL
    ap2: [ 65000 ]                  # Single-entry AS-path ACL
    ap3:                            # AS-path ACL
    - action: deny
      path: [ 65000, 65001 ]        # The first entry is a list of ASNs
    - '6510.'                       # The second entry is a regexp
```

_netlab_ normalizes these AS-path filters into the following data structure:

```
aspath:
  ap1:
  - action: permit
    path: 65000
    sequence: 10
  ap2:
  - action: permit
    path: 65000
    sequence: 10
  ap3:
  - action: deny
    path: 65000 65001
    sequence: 10
  - action: permit
    path: '6510.'
    sequence: 20
```

(generic-routing-community)=
## BGP Community Filters

BGP community filters are lists of conditions (usually known as *community lists*) that permit or deny BGP routes based on standard BGP communities attached to them. They can match a list of communities or a regular expression. You can use them in the **match.community** parameters of routing policies to match BGP routes. Each BGP community filter entry can have these attributes:

* **action**: A prefix filter entry can **permit** or **deny** matched prefixes (default: **permit**)
* **sequence**: Statement sequence number. When not specified, *netlab* sets a prefix filter entry's **sequence** number to ten times its list position.
* **list**: A list of communities to match
* **regexp**: A regular expression to match

BGP community filters are specified in the global- or node-level **routing.community** dictionary. The dictionary keys are filter names (community-list names), and the dictionary values are BGP community filters (lists of BGP community filter entries).

The following example specifies a BGP community filter that drops BGP routes carrying communities defined by AS 65000 and permits everything else:

```
module: [ routing ]

routing.community:
  not_65000:
  - action: deny
    regexp: _65000:[0-9]+_
  - action: permit
```

### Shortcut BGP Community Filter Definitions

Filters encoded in YAML tend to be verbose, and we tried to do as much as we could to reduce BGP community filter verbosity:

* You can skip the **action** and **sequence** attributes.
* Each entry in a BGP community filter could be a simple string or a list of BGP communities to match. Such entries are converted into dictionaries with the **list** or **regexp** element set to the entry's value. _netlab_ automatically determines whether a value is a list of communities or a regular expression.
* A list of BGP communities in the **list** element is converted into a string of BGP communities separated by a blank
* A BGP community filter could be a single string. That string is first converted into a list and subsequently into a list containing a single dictionary.
* _netlab_ automatically generates an *expanded* community list if at least one entry contains a regular expression, and a *standard* community list if all entries contain community values or lists of them.

The following example lists various shortened definitions of BGP community filters:

```
routing.community:
  cl1: 65000:100                            # Single-entry ACL
  cl2: [ 65000:100, 65000:101 ]             # Single-entry multivalue ACL
  cl3: _65000:10[1-2]_                      # Regular expression
  cl4:                                      # More complex standard ACL
  - action: permit                          # Used to implement or-of-ands condition
    path: [ 65000:100, 65001:100 ]
  - action: permit
    path: [ 65000:103, 65001:103 ]
  cl5:                                      # A mix of standard and extended conditions ==> extended
  - action: deny
    path: [ 65000:100, 65001:100 ]          # first entry is a list of communities
  - '_6510.:307_'                           # the second entry is a regexp
  cl6:                                      # Permit any at the end forces an extended clist
  - action: deny
    path: [ 65000:100, 65001:100 ]
  - action: permit
```

_netlab_ normalizes these BGP community filters into the following data structure:

```
community:
  cl1:
    - list: 65000:100
      action: permit
      sequence: 10
  cl2:
    - list: 65000:100
      action: permit
      sequence: 10
    - list: 65000:101
      action: permit
      sequence: 20
  cl3:
    - action: permit
      regexp: _65000:10[1-2]_
      sequence: 10
  cl4:
    value:
    - list: 65000:100 65001:100
      action: permit
      sequence: 10
    - list: 65000:103 65001:103
      action: permit
      sequence: 20
  cl5:
    value:
    - list: 65000:100 65001:100
      action: deny
      sequence: 10
    - action: permit
      regexp: _6510.:307_
      sequence: 20
  cl6:
    value:
    - list: 65000:100 65001:100
      action: deny
      sequence: 10
    - action: permit
      regexp: .*
      sequence: 20
```

(generic-routing-static)=
## Static Routes

Static routes are defined as lists of prefix/next-hop pairs in the **routing.static** node attribute. Each static route entry must specify a prefix and a next hop.

### Platform Support

_netlab_ supports static routes on these platforms:

| Operating system    | Global<br>static routes | Discard<br>routes | VRF static<br>routes | Inter-VRF<br>static routes |
|---------------------|:--:|:--:|:--:|:--:|
| Arista EOS          | ✅ | ✅ | ✅ | ✅ |
| Aruba AOS-CX        | ✅ | ✅ | ✅ | [❗](caveats-aruba) |
| Cisco IOS/XE[^18v]  | ✅ | ✅ | ✅ | ✅ |
| Cumulus Linux 4.x   | ✅ |  ❌ | ✅ | ✅ |
| Dell OS10           | ✅ | ✅ | ✅ | ✅ |
| Junos               | ✅ | ✅ | ✅ | ❌ |
| FRR                 | ✅ | ✅ | ✅ | ✅ |
| Linux               | ✅ |  ❌ |  ❌ |  ❌ |
| VyOS                | ✅ | ✅ | ✅ | ✅ |

### Configuring Static Routes

The static route prefix can be defined with one of these attributes:

* **ipv4**/**ipv6** -- an IPv4 and/or IPv6 prefix
* **pool** -- [address pool](address-pools) prefix
* **prefix** -- a [named prefix](named-prefixes)
* **node** -- a prefix of the specified node's control-plane endpoint (loopback interface or first data-plane interface)

```{tip}
You can combine **‌ipv4** and **‌ipv6** prefixes in the same static route entry. All other attributes are exclusive and can specify both IPv4 and IPv6 prefixes.
```

A static route entry's **nexthop** attribute specifies the next hop used to reach the specified prefixes. The next hop can be defined with any one of these attributes:

* **ipv4**/**ipv6** -- an IPv4 and/or IPv6 next hop (an address, not a prefix)
* **gateway** (boolean) -- the next hop is the default gateway. This entry will be resolved into a list containing all directly connected default gateways in the specified next-hop VRF (a node might use more than one default gateway to reach a destination).
* **node** -- The next hop is the specified node. The node name will be resolved into a list of directly connected next-hops or the control-plane endpoint of a distant node (allowing you to specify recursive static routes).
* **discard** -- The static route is a *discard* (aka *blackhole*) route pointing to the *null* interface (or an equivalent).

```{tip}
* You can combine **‌ipv4** and **‌ipv6** next hops in the same static route entry. **gateway** and **node** next-hop attributes are exclusive and can specify both IPv4 and IPv6 next hops.
* Static route entries with an **‌ipv4** prefix must have an **‌ipv4** next hop (and likewise for **‌ipv6**). _netlab_ does not support IPv6 next hops for IPv4 routes.
* _netlab_ will configure several static routes with different next hops if your topology has multiple direct links between the source and the next-hop node or if a node is attached to multiple links with default gateways.
* Static routes cannot point to unnumbered IPv4 interfaces or LLA-only IPv6 interfaces.
```

For example, the following lab topology generates two static routes on node C for the loopback address of node X, pointing to the directly connected IP addresses of node P:

```
nodes:
  c:
    module: [ routing ]
    routing.static:
    - node: x
      nexthop.node: p
  p:
    module: [ ospf ]
  x:
    module: [ ospf ]

links: [ c-p, c-p, p-x ]
```

After adding the static route for the loopback address of node X, we can add a static default route using that loopback address as the next hop:

```
nodes:
  c:
    module: [ routing ]
    routing.static:
    - node: x
      nexthop.node: p
    - ipv4: 0.0.0.0/0
      nexthop.node: x
  p:
    module: [ ospf ]
  x:
    module: [ ospf ]

links: [ c-p, c-p, p-x ]
```

The following topology will add a default route toward the anycast default gateway:

```
nodes:
  c:
    module: [ routing ]
    routing.static:
    - ipv4: 0.0.0.0/0
      gateway: True
  s1:
    module: [ gateway ]
  s2:
    module: [ gateway ]

links:
- interfaces: [ c, s1, s2 ]
  gateway.protocol: anycast
```

In the following topology, the node C is attached to two interfaces with a default gateway. _netlab_ will configure two static default routes (one per default gateway):

```
nodes:
  c:
    module: [ routing ]
    routing.static:
    - ipv4: 0.0.0.0/0
      gateway: True
  s1:
    module: [ gateway ]
  s2:
    module: [ gateway ]

links:
- interfaces: [ c, s1, s2 ]
  gateway.protocol: anycast
- interfaces: [ c, s1, s2 ]
  gateway.protocol: anycast
```

### VRF Static Routes

You can specify the **vrf** attribute in a static route entry to create a VRF static route. The lack of a **vrf** attribute indicates a static route in the global routing table (sometimes called *default VRF*).

You can also specify the **vrf** attribute in the next-hop definition to create an inter-VRF static route. Use the **nexthop.vrf** attribute with no value (`null`) to create a VRF static route with a next hop in the global routing table.

### Global Static Routes

You can define global static routes in the **routing.static** topology attribute. The definition of global static routes is a dictionary of static route lists, allowing you to include a subset of global static routes into individual nodes.

To include a global static route list into the node static routes, use the **include** attribute in a node static route entry. For example, you could use the following definitions to include the default routes pointing to node X into node C:

```
routing.static:
  default:
  - ipv4: 0.0.0.0/0
    ipv6: ::/0
    nexthop.node: x

module: [ ospf ]

nodes:
  c:
    module: [ routing,ospf ]
    routing.static:
    - include: default
  p:
  x:

links: [ c-p, p-x ]
```

You can override the next hop of the included static routes with the **nexthop** attribute specified in the **include** entry. For example, you can change the next hop of the default route on the C router to point to the upstream P router:

```
routing.static:
  default:
  - ipv4: 0.0.0.0/0
    ipv6: ::/0
    nexthop.node: x

module: [ ospf ]

nodes:
  c:
    module: [ routing ]
    routing.static:
    - include: default
      nexthop.node: p
  p:
  x:

links: [ c-p, p-x ]
```

## Advanced Topics

(routing-object-import)=
### Using Global- and Node-Level Routing Objects

A routing object (routing policy, prefix filter, BGP AS-path filter, or BGP community filter) will not be configured on a network device if it's not defined within the node **routing._object_** dictionary.

That's usually not a problem as the users of routing policies (for example, the [**bgp.policy** plugin](plugin-bgp-policy)) copy global routing policies and all filters used by those routing policies into node data whenever the lab topology references a global routing policy, or when a local routing policy references a global filter. However, you might need a placeholder routing object that is later used in a custom template. To force a global routing object to be copied and configured on a node, mention its name in the corresponding node **routing** dictionary without giving it a value.

For example, use the following code snippet if you want to have *route map* P1 defined on node R1 even though no _netlab_ configuration construct uses it:

```
routing.policy:
  p1:
  - set.locpref: 100
  
nodes:
  r1:
    routing.policy.p1:
```

The above lab topology will copy the contents of the P1 global routing policy into the R1 **routing.policy** dictionary, resulting in the corresponding route map configured on R1.

(routing-object-merge)=
### Merging Routing Objects

When a routing object (routing policy, prefix filter, BGP AS-path filter, or BGP community filter) is defined globally as well as within a node, _netlab_ tries to merge the two definitions based on the sequence numbers attached to the routing object entries:

* Global routing object entries with sequence numbers that do not exist in the node-level routing object are added to that object.
* The resulting list is sorted based on the sequence numbers.

For example, consider the following routing policy definitions:

```
routing.prefix:
  loopbacks:
  - pool: loopback

routing.policy:
  p1:
  - match.prefix: loopbacks
    set.locpref: 100
  - set.med: 200
  
nodes:
  r1:
    routing.policy:
      p1:
      - match.prefix: loopbacks
        set.locpref: 200
      - sequence: 15
        set.prepend.path: 65000
```

The entries in routing policies without sequence numbers get their sequence numbers assigned based on their position in the routing policy list. The above example is thus equivalent to:

```
routing.policy:
  p1:
  - sequence: 10
    match.prefix: loopbacks
    set.locpref: 100
  - sequence: 20
    set.med: 200
  
nodes:
  r1:
    routing.policy:
      p1:
      - sequence: 10
        match.prefix: loopbacks
        set.locpref: 200
      - sequence: 15
        set.prepend.path: 65000
```

The results of the merging process should now be self-explanatory. The sequence number 20 is missing from the node-level routing policy. That entry is added from the global routing policy, and the results are sorted, giving us the following routing policy on R1:

```
p1:
- sequence: 10
  match.prefix: loopbacks
  set.locpref: 200
- sequence: 15
  set.prepend.path: 65000
- sequence: 20
  set.med: 200
```
