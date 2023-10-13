# BGP Sessions Plugin

The **bgp.session** plugin (initially contributed by Stefano Sasso) implements numerous BGP session ~~nerd knobs~~ attributes, from BGP session protection to AS path manipulation.

## Supported BGP Attributes

The plugin adds the following BGP session attributes:

* **bgp.allowas_in** is an attribute that controls whether a BGP router accepts one or more copies of its own AS number in incoming update. It takes an integer value between 1 and 10. A *true* value sets it to 1.
* **bgp.as_override** is a boolean attribute that controls whether a BGP router replaces peer AS with its own AS.
* **bgp.bfd** is a boolean attribute that enables BFD with BGP neighbors.
* **bgp.default_originate** is a boolean attribute that controls whether a BGP router advertises a default route to its neighbor(s).
* **bgp.gtsm** is an integer attribute that enables the Generic TTL Security Mechanism (GTSM). A *true* value sets it to 1 (remote router can be up to one hop away).
* **bgp.password** is a string attribute that specifies the MD5  or TCP-AO password used on EBGP sessions.
* **bgp.tcp_ao** is an attribute that enables TCP-AO on a BGP session. The attribute value *true* enables TCP-AO with HMAC-SHA1-96 algorithm; you can specify the desired algorithm as a string value of **bgp.tcp_ao** parameter.
* **bgp.timers** is a dictionary of BGP session timers. It has three elements:

	* **bgp.timers.keepalive** -- keepalive timer in seconds
	* **bgp.timers.hold** -- hold timer in seconds
	* **bgp.timers.min_hold** -- minimum hold timer accepted from the remote node. Used only on devices where the minimum hold timer can be specified per BGP neighbor.

BGP session attributes can be specified on global, node, link, or interface (node-to-link attachment) level. The following table describes where you could apply individual attributes:

| BGP session attribute | Global | Node | Link | Interface |
|-----------------------|:------:|:----:|:----:|:---------:|
| allowas_in            |    ❌   |  ❌   |  ❌   |    ✅     |
| as_override           |    ❌   |  ❌   |  ❌   |    ✅     |
| bfd                   |   ✅   |  ✅  |  ✅  |    ✅     |
| default_originate     |    ❌   |  ✅  |  ❌   |    ✅     |
| gtsm                  |   ✅   |  ✅  |  ✅  |    ✅     |
| password              |   ✅   |  ✅  |  ✅  |    ✅     |
| tcp_ao                |   ✅   |  ✅  |  ✅  |    ✅     |
| timers                |   ✅   |  ✅  |  ✅  |    ✅     |

## Platform Support

The plugin implements generic BGP session features for the following platforms:

| Operating system    | password | default<br>originate | GTSM | BGP<br>timers | TCP-AO | BFD |
| ------------------- | :------: | :---------------: | :--: | :--: | :--: | :-: |
| Arista EOS          |    ✅    |     ✅                | ✅  | ✅  | ✅  | ✅ |
| Cisco IOSv          |    ✅    |    ✅                | ✅  | ✅  |  ❌  | ✅ |
| Cisco IOS-XE        |    ✅    |    ✅                | ✅  | ✅  | ✅  | ✅ |
| Cumulus Linux       |    ✅    |    ✅                | ✅  | ✅  |  ❌  | ✅ |
| FRR                 |    ✅    |    ✅                | ✅  | ✅  |  ❌  | ❌  |
| Juniper vMX/vPTX/vSRX |    ✅    |    ❌                 |  ❌  |  ❌  |  ❌  | ❌  |
| Mikrotik RouterOS 7 |    ✅    |    ✅                |  ❌  |  ❌  |  ❌  | ❌  |
| Nokia SR Linux      |    ✅    |    ✅                |  ❌  |  ❌  |  ❌  | ❌  |
| Nokia SR OS         |    ✅    |    ✅                |  ❌  |  ❌  | ✅  | ❌  |
| VyOS                |    ✅    |    ✅                |  ❌  |  ❌  |  ❌  | ❌  |

**Notes:**
* Arista EOS supports TCP-AO only when running as a virtual machine
* _netlab_ always configures HMAC-SHA1-96 as the cryptographic algorithm on IOS XE

The plugin implements AS-path-mangling nerd knobs for the following platforms:

| Operating system    | allowas_in | AS<br>override |
| ------------------- | :--------: | :---------: |
| Arista EOS          |      ✅    |     ✅      |
| Cisco IOSv          |      ✅    |     ✅      |
| Cisco IOS-XE        |      ✅    |     ✅      |
| Cumulus Linux       |      ✅    |     ✅      |
| FRR                 |      ✅    |     ✅      |
| Juniper vMX/vPTX/vSRX |     ❌    |     ✅      |
| Mikrotik RouterOS 7 |      ✅    |     ✅      |
| Nokia SR Linux      |      ✅    |     ✅      |
| Nokia SR OS         |      ✅    |     ✅      |
| VyOS                |      ✅    |     ✅      |

## Applying BGP Session Attributes to IBGP Sessions

The plugin applies BGP session attributes to EBGP sessions -- either all EBGP sessions a node has if the attribute has been specified on a global- or node level, or all EBGP sessions on a link where the BGP session attribute has been specified.

If you want to apply BGP session attributes to IBGP sessions, you have to set the **bgp.session.apply** global/node parameter -- a list or a dictionary of BGP neighbor types to which the BGP session attributes are applied. The default behavior is equivalent to `bgp.session.apply: [ ebgp ]`; if you want to apply the session attributes to IBGP and EBGP sessions, specify `bgp.session.apply: [ ibgp, ebgp ]` as a global or node attribute.

IBGP sessions are not associated with links/interfaces and therefore cannot inherit the BGP session parameters specified on links or interfaces -- only the parameters specified on global- or node level are applied to IBGP sessions. For example, to use MD5 password `secret` on all IBGP and EBGP sessions in your lab, use the following global settings:

```
bgp.session.apply: [ ibgp, ebgp ]
bgp.password: secret
```

If you don't want to apply all node-level BGP session parameters to IBGP sessions, you could use the dictionary format of **bgp.session.apply** parameter: the BGP neighbor types are the dictionary keys, the values are lists of parameters that you want to apply to IBGP and EBGP sessions (missing value means _apply all parameters_).

For example, the node settings from the next example cause the BGP password to be applied to IBGP and EBGP sessions, while all other BGP session parameters (including the default route origination) are applied only to EBGP sessions:

```
bgp.password: secret

nodes:
  core:
    bgp.default_originate: True
    bgp.session.apply:
      ibgp: [ password ]
      ebgp:
```

The following example is even more specific: default route origination and a few AS-related session parameters (but not MD5 password) are applied to EBGP sessions, while the MD5 passwords are applied only to IBGP sessions:

```
bgp.password: secret
bgp.session.apply:
  ibgp: [ password ]
  ebgp: [ default_originate, allowas_in, as_override ]
```

## Test Topology

The following test topology illustrates a subset of plugin capabilities. You might also want to explore the topologies used in [ipSpace.net BGP labs](https://github.com/ipspace/bgplab) and the [BGP session plugin test topology](https://github.com/ipspace/netlab/blob/dev/tests/topology/input/ebgp.utils.yml).

```
---
defaults:
  device: eos

module: [ bgp, vrf ]
plugin: [ bgp.session ]

vrfs:
  red:
  blue:

bgp.timers:
  hold: 10
  keepalive: 3

nodes:
  y1:
    bgp.as: 65001
  y2:
    bgp.as: 65002

links:
- y1:
    bgp.default_originate: True
  y2:
  bgp.password: TestPassword
- y1:
    vrf: red
  y2:
    vrf: red
    bgp.allowas_in: True
    bgp.default_originate: True
- y1:
    vrf: blue
  y2:
    vrf: blue
    bgp.as_override: True
```
