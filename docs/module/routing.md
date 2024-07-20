(generic-routing)=
# Generic Routing Configuration Module

This configuration module implements generic routing features:

* [Routing policies (route maps)](generic-routing-policies)
* Prefix filters (TBD)
* AS-path filters (TBD)
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
| Arista EOS          |  ✅  |
| Aruba AOS-CX        |  ✅  |
| Cisco IOSv          |  ✅  |
| Cisco IOS-XE[^18v]  |  ✅  |
| Cumulus Linux       |  ✅  |
| FRR                 |  ✅  |
| Nokia SR Linux      |  ✅  |
| Nokia SR OS         |  ✅  |
| VyOS                |  ✅  |

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

* Unambiguous keywords like **med** and **locpref** do not need to be within the **set** dictionary. *netlab* automatically moves them into the routing-policy-entry **set** dictionary. For example, the following two routing policies are equivalent:

```
routing.policy:
  p1:
  - set.locpref: 100
  p2:
    locpref: 100
```

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

### Merging Routing Policies

When a routing policy is defined globally as well as within a node, _netlab_ tries to merge the two definitions based on the sequence numbers attached to the routing policy entries:

* Global routing policy entries with sequence numbers that do not exist in the node-level routing policy are added to that routing policy.
* The resulting list is sorted based on the sequence numbers.

For example, consider the following routing policy definitions[^MGMNS]:

[^MGMNS]: The example has no real-life significance as the first entry in a route map matches all routes, and the subsequent entries are never evaluated. We'll fix it once we get the **match** conditions implemented ;)

```
routing.policy:
  p1:
  - set.locpref: 100
  - set.med: 200
  
nodes:
  r1:
    routing.policy:
      p1:
      - set.locpref: 200
      - sequence: 15
        set.prepend.path: 65000
```

The entries in routing policies without sequence numbers get their sequence numbers assigned based on their position in the routing policy list. The above example is thus equivalent to:

```
routing.policy:
  p1:
  - sequence: 10
    set.locpref: 100
  - sequence: 20
    set.med: 200
  
nodes:
  r1:
    routing.policy:
      p1:
      - sequence: 10
        set.locpref: 200
      - sequence: 15
        set.prepend.path: 65000
```

The results of the merging process should now be self-explanatory. The sequence number 20 is missing from the node-level routing policy. That entry is added from the global routing policy, and the results are sorted, giving us the following routing policy on R1:

```
p1:
- sequence: 10
  set.locpref: 200
- sequence: 15
  set.prepend.path: 65000
- sequence: 20
  set.med: 200
```
