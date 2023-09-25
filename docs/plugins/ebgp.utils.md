# EBGP Utilities

The **ebgp.utils** plugin (contributed by Stefano Sasso) implements several EBGP nerd knobs, including:

* **bgp.allowas_in** is an interface (node-to-link attachment) attribute that controls whether a BGP router accepts one or more copies of its own AS number in incoming update. It takes an integer value between 1 and 10. A *true* value sets it to 1.
* **bgp.as_override** is an interface (node-to-link attachment) boolean attribute that controls whether a BGP router replaces peer AS with its own AS.
* **bgp.default_originate** is a boolean attribute that controls whether a BGP router advertises a default route to its neighbor(s). It can be specified on global, node, link or interface level.
* **bgp.gtsm** is an integer attribute that enables the Generic TTL Security Mechanism (GTSM). It can be specified on global, node, link or interface level and takes an integer value between 1 and 254. A *true* value sets it to 1 (remote router can be up to one hop away).
* **bgp.password** is a string attribute that can be specified on global, node, link or interface level. It specifies the MD5 password used on EBGP sessions.

The plugin includes Jinja2 templates for the following platforms:

| Operating system    | allowas_in | AS<br>override | password | default<br>originate | GTSM |
| ------------------- | :--------: | :---------: | :------: | :---------------: | :--: |
| Arista EOS          |      ✅    |     ✅      |    ✅    |     ✅                | ✅  |
| Cisco IOSv / IOS-XE |      ✅    |     ✅      |    ✅    |    ✅                | ✅  |
| Cumulus Linux       |      ✅    |     ✅      |    ✅    |    ✅                | ✅  |
| FRR                 |      ✅    |     ✅      |    ✅    |    ✅                | ✅  |
| Juniper vMX/vPTX/vSRX |     ❌    |     ✅      |    ✅    |    ❌                 |  ❌  |
| Mikrotik RouterOS 7 |      ✅    |     ✅      |    ✅    |    ✅                |  ❌  |
| Nokia SR Linux      |      ✅    |     ✅      |    ✅    |    ✅                |  ❌  |
| Nokia SR OS         |      ✅    |     ✅      |    ✅    |    ✅                |  ❌  |
| VyOS                |      ✅    |     ✅      |    ✅    |    ✅                |  ❌  |

## Test Topology

```
---
defaults:
  device: eos

module: [ bgp, vrf ]
plugin: [ ebgp.utils ]

vrfs:
  red:
  blue:

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
