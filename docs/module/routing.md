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
* **sequence**: Statement sequence number. When not specified, *netlab* sets the **sequence** number of a routing policy entry to ten times its list position.
* **match**: Parameters that have to match for the routing policy entry to take effect. Entries without a **match** parameter match all routes
* **set**: Parameters that are set on matched routes.

You can set these route parameters in a _netlab_ routing policy:

* **locpref**: BGP local preference
* **med**: Route metric (for example, BGP MED)
* **prepend**: BGP AS-path prepending ([more details](plugin-bgp-policy-attributes))
* **weight**: BGP weight

Routing policies are specified in the global- or node-level **routing.policy** dictionary. The dictionary keys are policy names (route map names), and the dictionary values are routing policies (lists of routing policy entries).

The following example specifies two global routing policies setting BGP local preference to different values, and a node routing policy setting MED.

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

TBD

### Merging Routing Policies

TBD
