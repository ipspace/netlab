# EBGP Utilities

The **ebgp.utils** plugin (contributed by Stefano Sasso) implements several EBGP nerd knobs, including: **allowas_in**, **as_override**, **default_originate** and MD5 **password**:

* **bgp.allowas_in** is an interface (node-to-link attachment) attribute that takes an integer value between 1 and 10. A *true* value sets it to 1.
* **bgp.as_override** is an interface (node-to-link attachment) boolean attribute.
* **bgp.default_originate** is an interface (node-to-link attachment) boolean attribute.
* **bgp.password** is a link-level string attribute.

The plugin includes Jinja2 templates for Cisco IOS, Arista EOS and VyOS.

| Operating system         | allowas_in | as_override | password | default_originate |
| ------------------------ | :--------: | :---------: | :------: | :---------------: |
| Arista EOS               |      ✅    |     ✅      |    ✅    |    ✅    |
| Cisco IOS                |      ✅    |     ✅      |    ✅    |    ✅    |
| VyOS                     |      ✅    |     ✅      |    ✅    |    ✅    |

**NOTES**:
* VyOS always originates a defaults when *default_originate* is set. Arista EOS originates a default only if present in the routing table, unless *always* is specified.

## Test Topology

```
---
provider: clab
defaults.device: eos
module: [ bgp ]
plugin: [ ebgp.utils ]

nodes:
  r1:
    bgp.as: 65101
  r2:
    bgp.as: 65000
  r3:
    bgp.as: 65101

links:
- r1:
    bgp.allowas_in: True
    bgp.default_originate: True
  r2:
- bgp.password: Test
  r2:
    bgp.as_override: True
  r3:
```
