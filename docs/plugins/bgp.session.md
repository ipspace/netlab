# BGP Sessions Plugin

The **bgp.session** plugin (initially contributed by Stefano Sasso) implements numerous BGP session ~~nerd knobs~~ attributes, from BGP session protection to AS path manipulation.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Supported BGP Attributes

The plugin adds the following BGP session attributes:

* **bgp.allowas_in** is an attribute that controls whether a BGP router accepts one or more copies of its own AS number in incoming update. It takes an integer value between 1 and 10. A *true* value sets it to 1.
* **bgp.as_override** is a boolean attribute that controls whether a BGP router replaces peer AS with its own AS.
* **bgp.bfd** is a boolean attribute that enables BFD with BGP neighbors.
* **bgp.default_originate** is a boolean attribute that controls whether a BGP router advertises a default route to its neighbor(s).
* **bgp.gtsm** is an integer attribute that enables the Generic TTL Security Mechanism (GTSM). A *true* value sets it to 1 (remote router can be up to one hop away).
* **bgp.passive** is a boolean attribute that makes a node act as a passive BGP peer[^PBP] on an interface or on all applicable sessions (when specified as a node parameter).
* **bgp.password** is a string attribute that specifies the MD5  or TCP-AO password used on EBGP sessions.
* **bgp.remove_private_as** is a boolean/string/list attribute that describes the desired removal of private autonomous system(s) from AS path. See [](bgp-session-remove-private-as) section for more details.
* **bgp.tcp_ao** is an attribute that enables TCP-AO on a BGP session. The attribute value *true* enables TCP-AO with HMAC-SHA1-96 algorithm; you can specify the desired algorithm as a string value of **bgp.tcp_ao** parameter.
* **bgp.timers** is a dictionary of BGP session timers. It has three elements:

	* **bgp.timers.keepalive** -- keepalive timer in seconds
	* **bgp.timers.hold** -- hold timer in seconds
	* **bgp.timers.min_hold** -- minimum hold timer accepted from the remote node. Used only on devices where the minimum hold timer can be specified per BGP neighbor.

[^PBP]: A passive BGP peer waits for its neighbor to initiate the conversation and never tries to establish a TCP session with its neighbor.

BGP session attributes can be specified on global, node, link, or interface (node-to-link attachment) level. The following table describes where you could apply individual attributes:

| BGP session attribute | Global | Node | Link | Interface |
|-----------------------|:------:|:----:|:----:|:---------:|
| allowas_in            |    ❌   |  ❌   |  ❌   |    ✅     |
| as_override           |    ❌   |  ❌   |  ❌   |    ✅     |
| bfd                   |   ✅   |  ✅  |  ✅  |    ✅     |
| default_originate     |    ❌   |  ✅  |  ❌   |    ✅     |
| gtsm                  |   ✅   |  ✅  |  ✅  |    ✅     |
| passive               |    ❌   |  ✅  |   ❌  |    ✅     |
| password              |   ✅   |  ✅  |  ✅  |    ✅     |
| remove_private_as     |    ❌   |  ❌   |  ❌   |    ✅     |
| tcp_ao                |   ✅   |  ✅  |  ✅  |    ✅     |
| timers                |   ✅   |  ✅  |  ✅  |    ✅     |

## Platform Support

The plugin implements generic BGP session features for the following platforms:

(bgp-session-platforms)=
| Operating system    | default<br>originate | BGP<br>timers |  BFD | Passive<br>peer |
| ------------------- | :--: | :--: | :--: | :--: |
| Arista EOS          |  ✅  |  ✅  |  ✅  |  ✅  |
| Aruba AOS-CX        |  ✅  |  ✅  |  ✅  |   ❌  |
| Cisco IOSv          |  ✅  |  ✅  |  ✅  |  ✅  |
| Cisco IOS-XE        |  ✅  |  ✅  |  ✅  |  ✅  |
| Cumulus Linux       |  ✅  |  ✅  |  ✅  |  ✅  |
| FRR                 |  ✅  |  ✅  |  ✅  |  ✅  |
| Mikrotik RouterOS 7 |  ✅  |   ❌  |   ❌  |   ❌  |
| Nokia SR Linux      |  ✅  |   ✅  |   ✅  |   ✅  |
| Nokia SR OS         |  ✅  |   ❌  |   ❌  |   ❌  |
| VyOS                |  ✅  |   ❌  |   ❌  |   ❌  |

**Notes:**
* Arista EOS supports TCP-AO only when running as a virtual machine
* _netlab_ always configures HMAC-SHA1-96 as the cryptographic algorithm on IOS XE

(bgp-session-security)=
BGP session security features are available on these platforms:

| Operating system    | password | GTSM | TCP-AO |
| ------------------- | :------: | :-: | :-: |
| Arista EOS          |    ✅    | ✅  | ✅  |
| Aruba AOS-CX        |    ✅    | ✅  |  ❌  |
| Cisco IOSv          |    ✅    | ✅  |  ❌  |
| Cisco IOS-XE        |    ✅    |  ✅ |  ✅ |
| Cumulus Linux       |    ✅    | ✅  |  ❌  |
| FRR                 |    ✅    | ✅  |  ❌  |
| Juniper vMX/vPTX/vSRX |    ✅  |  ❌  |  ❌  |
| Mikrotik RouterOS 7 |      ✅  |  ❌  |  ❌  |
| Nokia SR Linux      |     ✅   |  ❌  |  ❌  |
| Nokia SR OS         |     ✅   |  ❌  | ✅  |

(bgp-session-as-path)=
The plugin implements AS-path-mangling nerd knobs for the following platforms:

| Operating system    | Allow<br>AS in | AS<br>override | Remove<br>private AS |
| ------------------- | :--: | :--: | :--: |
| Arista EOS          |  ✅  |  ✅  |  ✅  |
| Aruba AOS-CX        |  ✅  |  ❌  |  ✅  |
| Cisco IOSv          |  ✅  |  ✅  |  ✅  |
| Cisco IOS-XE        |  ✅  |  ✅  |  ✅  |
| Cumulus Linux       |  ✅  |  ✅  |  ✅  |
| FRR                 |  ✅  |  ✅  |  ✅  |
| Juniper vMX/vPTX/vSRX | ❌  |  ✅  |   ❌  |
| Mikrotik RouterOS 7 |  ✅  |  ✅  |   ❌  |
| Nokia SR Linux      |  ✅  |  ✅  |   ✅  |
| Nokia SR OS         |  ✅  |  ✅  |   ❌  |
| VyOS                |  ✅  |  ✅  |   ❌  |

(bgp-session-apply)=
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

(bgp-session-remove-private-as)=
## Remove Private AS Options

This plugin accepts the following values of the **bgp.remove_private_as** attribute.

* **True** (or **on**[^QON]): enable simple removal of private AS on egress updates
* **all**: remove all instances of private AS numbers in egress updates
* **replace**: replace all instances of private AS number with the router's own AS number in egress updates
* **ingress**: remove private AS numbers from ingress updates
* **ingress-replace**: replace all private AS numbers with peer AS number in ingress updates

[^QON]: You have to quote the **on** string, otherwise the Python YAML parser treats it as a boolean. For example, you have to specify `bgp.remove_private_as: [ 'on', ingress ]`

You can specify the **bgp.remove_private_as** attribute as a boolean value (equivalent to **on**), as a single string value, or as a list of string values in case you have to specify egress and ingress behavior.

The implementations of **neighbor remove-private-as** command vary widely across supported network devices as described in the following table:

| Operating system    | on | all | replace | ingress | ingress-replace |
| ------------------- | :--: | :--: | :--: | :--: | :--: |
| Arista EOS          |  ✅  |  ✅  |  ✅  |  ✅  |  ✅  |
| Cisco IOSv          |  ✅  |  ❗  |  ❗  |   ❌  |   ❌  |
| Cisco IOS-XE        |  ✅  |  ❗  |  ❗  |   ❌  |   ❌  |
| Cumulus Linux       |  ✅  |  ✅  |  ✅  |   ❌  |   ❌  |
| FRR                 |  ✅  |  ✅  |  ✅  |   ❌  |   ❌  |
| Nokia SR Linux      |  ✅  |  ✅  |  ✅  |   ❌  |   ❌  |

**Notes:**

* Cisco IOSv/IOS-XE do not accept **all** or **replace** option when the local BGP AS number is a private AS number.

## Test Topology

The following test topology illustrates a subset of plugin capabilities. You might also want to explore the topologies used in [ipSpace.net BGP labs](https://github.com/ipspace/bgplab) and the [BGP session plugin test topology](https://github.com/ipspace/netlab/blob/dev/tests/topology/input/ebgp.utils.yml).

```
---
defaults:
  device: eos

module: [ bgp, vrf, bfd ]
plugin: [ bgp.session ]

vrfs:
  red:
  blue:

bgp.timers:
  hold: 10
  keepalive: 3

bgp.bfd: True

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
