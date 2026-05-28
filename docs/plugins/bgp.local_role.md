(plugin-bgp-local-role)=
# BGP Local Role Plugin

The **bgp.local_role** plugin configures [RFC 9234](https://www.rfc-editor.org/rfc/rfc9234.html) BGP Roles on EBGP sessions. BGP Roles negotiate the peering relationship in the BGP OPEN message and enable automatic Only-to-Customer (OTC) handling for route-leak prevention.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Supported BGP Attributes

* **bgp.local_role** -- the local BGP role for an EBGP session. Valid values: **provider**, **customer**, **peer**, **rs-server**, **rs-client**.
* **bgp.local_role_strict** -- when set to _true_, the BGP session is established only if the remote router also advertises a compatible BGP Role capability (RFC 9234 strict mode).

BGP local role attributes can be specified at the global, node, link, or interface level:

| BGP local role attribute | Global | Node | Link | Interface |
|--------------------------|:------:|:----:|:----:|:---------:|
| local_role               |   ✅   |  ✅  |  ✅  |    ✅     |
| local_role_strict        |   ✅   |  ✅  |  ✅  |    ✅     |

The plugin applies these attributes to **EBGP** neighbors only. Using **bgp.local_role** on IBGP sessions results in a configuration error.

## Role Pairing

When both routers implement RFC 9234, the local role on one router must match the expected remote role on the other:

| Local role | Remote role |
|------------|-------------|
| provider   | customer    |
| customer   | provider    |
| peer       | peer        |
| rs-server  | rs-client   |
| rs-client  | rs-server   |

## Platform Support

(bgp-local-role-platforms)=
| Operating system | BGP Roles | Strict mode |
| ---------------- | :-------: | :---------: |
| FRR              |     ✅     |      ✅      |
| BIRD             |     ✅     |      ✅      |

FRR implements BGP Roles starting with release 8.4. BIRD implements them starting with release 2.0.11.

On BIRD, local roles are rendered into the BGP module configuration file (`daemons/bird/bgp.j2`); the plugin does not deploy a separate configuration script.

This plugin is independent of the **[bgp.session](bgp.session.md)** plugin. You can use both plugins in the same lab; list **bgp.session** before **bgp.local_role** if you use route server session features:

```
plugin: [ bgp.session, bgp.local_role ]
```

## Example

```yaml
plugin: [ bgp.local_role ]
module: [ bgp ]

nodes: [ isp, customer, peer ]

links:
- isp:
    bgp.local_role: provider
  customer:
    bgp.local_role: customer
- isp:
    bgp.local_role: peer
  peer:
    bgp.local_role: peer
```

## Test Topology

Integration test cases are in the `tests/integration/bgp.local_role` directory. A sample topology file is in `tests/topology/input/bgp-local-role.yml`.
