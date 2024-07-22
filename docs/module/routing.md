(generic-routing)=
# Generic Routing Configuration Module

This configuration module implements generic routing features:

* [Routing policies (route maps)](generic-routing-policies)
* [Prefix filters (prefix-lists)](generic-routing-prefixes)
* [AS-path filters](generic-routing-aspath)
* BGP community filters (TBD)
* Static routes (TBD)

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
| ------------------ | :-: | :-: | :-: |:-: | :-: |
| Arista EOS          |  ✅  |  ✅  |  ✅  |
| Aruba AOS-CX        |  ✅  |  ✅  |
| Cisco IOSv          |  ✅  |  ✅  |  ✅  |
| Cisco IOS-XE[^18v]  |  ✅  |  ✅  |  ✅  |
| Cumulus Linux       |  ✅  |  ✅  |  ✅  |
| FRR                 |  ✅  |  ✅  |  ✅  |
| Nokia SR Linux      |  ✅  |
| Nokia SR OS         |  ✅  |
| VyOS                |  ✅  |  ✅  |

```{tip}
See [Routing Integration Tests Results](https://release.netlab.tools/_html/coverage.routing) for more details.
```

[^18v]: Includes Cisco CSR 1000v and Cisco Catalyst 8000v

(generic-routing-policies)=
## Routing Policies

Routing policies are lists of instructions that can **match** route parameters and **set** route attributes. Each routing policy entry can have these attributes:

* **action**: A routing policy entry can **permit** or **deny** matched routes (default: **permit**)
* **sequence**: Statement sequence number. When not specified, *netlab* sets a routing policy entry's **sequence** number to ten times its list position.
* **match**: Conditions that must match for the routing policy entry to take effect. Entries without a **match** parameter match all routes
* **set**: Parameters that are set on matched routes.

You can set these route parameters in a _netlab_ routing policy:

* **locpref**: BGP local preference
* **med**: Route metric (for example, BGP MED)
* **prepend**: BGP AS-path prepending ([more details](plugin-bgp-policy-attributes))
* **weight**: BGP weight

Routing policies are specified in the global- or node-level **routing.policy** dictionary. The dictionary keys are policy names (route map names), and the dictionary values are routing policies (lists of routing policy entries).

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

You can use these routing policy **set** parameters on devices supported by the **routing** module:

| Operating system    | AS-path<br>prepend | Local<br>preference | MED | Weight |
|---------------------|:--:|:--:|:--:|:--:|
| Arista EOS          | ✅ | ✅ | ✅ | ✅ |
| Aruba AOS-CX        | ✅ | ✅ | ✅ | ✅ |
| Cisco IOSv          | ✅ | ✅ | ✅ | ✅ |
| Cisco IOS-XE[^18v]  | ✅ | ✅ | ✅ | ✅ |
| Cumulus Linux       | ✅ | ✅ | ✅ | ✅ |
| FRR                 | ✅ | ✅ | ✅ | ✅ |
| Nokia SR Linux      | ❌  | ✅ | ✅ | ❌  |
| Nokia SR OS         | ❌  | ✅ | ✅ | ❌  |
| VyOS                | ✅ | ✅ | ✅ | ❌  |

You can use these routing policy **match** parameters on devices supported by the **routing** module:

| Operating system    | IPv4/IPv6<br>prefix | IPv4/IPv6<br>next hop | BGP<br>AS-path | BGP<br>Community |
|---------------------|:--:|:--:|:--:|:--:|
| Arista EOS          | ✅ | ❌  | ✅ | ❌  |
| Aruba AOS-CX        | ✅ | ❌  | ❌  | ❌  |
| Cisco IOSv          | ✅ | ❌  | ✅ | ❌  |
| Cisco IOS-XE[^18v]  | ✅ | ❌  | ✅ | ❌  |
| Cumulus Linux       | ✅ | ❌  | ✅ | ❌  |
| FRR                 | ✅ | ❌  | ✅ | ❌  |
| VyOS                | ✅ | ❌  | ❌  | ❌  |

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

(routing-policy-import)=
### Using Global Routing Policies

A routing policy will not be configured as a route map on a network device if it's not defined within the node **routing.policy** dictionary.

That's usually not a problem as the users of routing policies (for example, the [**bgp.policy** plugin](plugin-bgp-policy)) copy global routing policies into node data whenever the lab topology references a global routing policy. However, you might need a placeholder routing policy that is later used in a custom template. To force a global routing policy to be copied and configured on a node, mention its name in the node **routing.policy** dictionary, for example:

```
routing.policy:
  p1:
  - set.locpref: 100
  
nodes:
  r1:
    routing.policy.p1:
```

The above lab topology will copy the contents of the P1 global routing policy into the R1 **routing.policy** dictionary, resulting in the corresponding route map configured on R1.

(routing-policy-merge)=
### Merging Routing Policies

When a routing policy is defined globally as well as within a node, _netlab_ tries to merge the two definitions based on the sequence numbers attached to the routing policy entries:

* Global routing policy entries with sequence numbers that do not exist in the node-level routing policy are added to that routing policy.
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

Prefix filters are specified in the global- or node-level **routing.prefix** dictionary. The dictionary keys are filter names (prefix-list names), and the dictionary values are prefix filters (lists of prefix filter entries).

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

### Using Global Prefix Filters

A prefix filter will not be configured as a `prefix-list` on a network device if it's not defined within the node **routing.prefix** dictionary.

That's usually not a problem as the users of prefix filters (for example, routing policies) copy global prefix filters into node data whenever the routing policy references a global prefix filter. However, you might need a placeholder prefix filter that is later used in a custom template. To force a global prefix filter to be copied and configured on a node, mention its name (without a value) in the node **routing.prefix** dictionary (see [](routing-policy-import) for related examples).

The two prefix filters are merged when a prefix filter is defined within the node *and* globally. See [](routing-policy-merge) for more details.

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

AS-path filters are specified in the global- or node-level **routing.aspath** dictionary. The dictionary keys are filter names (prefix-list names), and the dictionary values are AS-path filters (lists of AS-path filter entries).

The following example specifies an AS-path access list that drops BGP prefixes originated in AS 65000 and permits everything else:

```
module: [ routing ]

routing.aspath:
  not_65000:
  - action: deny
    path: _65000$
  - action: permit
```

### Using Global BGP AS-Path Filters

An AS-path filter will not be configured as an `ip as-path access-list` on a network device if it's not defined within the node **routing.aspath** dictionary.

That's usually not a problem as the users of AS-path filters (for example, routing policies) copy global definitions into node data whenever the routing policy references them. However, you might need a placeholder prefix filter that is later used in a custom template. To force a filter to be copied and configured on a node, mention its name (without a value) in the node **routing.aspath** dictionary (see [](routing-policy-import) for related examples).

The filters are merged when a BGP AS-path filter is defined within a node *and* globally. See [](routing-policy-merge) for more details.

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
