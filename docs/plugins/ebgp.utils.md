# EBGP Utilities

The **ebgp.utils** plugin (contributed by Stefano Sasso) implements several EBGP nerd knobs, including: **allowas_in**, **as_override**, **default_originate** and MD5 **password**:

* **bgp.allowas_in** is an interface (node-to-link attachment) attribute that takes an integer value between 1 and 10. A *true* value sets it to 1.
* **bgp.as_override** is an interface (node-to-link attachment) boolean attribute.
* **bgp.default_originate** is an interface (node-to-link attachment) attribute (True/False/*always*).
* **bgp.password** is a link-level string attribute.

The plugin includes Jinja2 templates for Cisco IOS, Arista EOS and VyOS.

| Operating system         | allowas_in | as_override | password | default_originate |
| ------------------------ | :--------: | :---------: | :------: | :---------------: |
| Arista EOS               |      ✅    |     ✅      |    ✅    |    ✅    |
| Cisco IOS                |      ✅    |     ✅      |    ✅    |    ✅    |
| Juniper vMX              |      ❌    |     ✅      |    ✅    |    ❌    |
| Juniper vSRX 3.0         |      ❌    |     ✅      |    ✅    |    ❌    |
| Mikrotik RouterOS 7      |      ✅    |     ✅      |    ✅    |    ✅    |
| VyOS                     |      ✅    |     ✅      |    ✅    |    ✅    |

**NOTES**:
* VyOS always originates a defaults when *default_originate* is set. Arista EOS originates a default only if present in the routing table, unless *always* is specified.

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
    bgp.default_originate: always
- y1:
    vrf: blue
  y2:
    vrf: blue
    bgp.as_override: True
```
