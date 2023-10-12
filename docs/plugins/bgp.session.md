# BGP Sessions Plugin

The **bgp.session** plugin (initially contributed by Stefano Sasso) implements several BGP session nerd knobs, including:

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


## Test Topology

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
