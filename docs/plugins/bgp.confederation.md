(plugin-bgp-confederation)=
# BGP Confederation Plugin

## Overview

This plugin adds support for **BGP Confederations**, as defined in [RFC 5065](https://datatracker.ietf.org/doc/html/rfc5065), to the Netlab topology definition. BGP Confederations are a scalability hack—not a magic bullet. They split a single autonomous system (AS) into smaller internal sub-ASes, pretending to the outside world that it's still one single AS.

Confederations are mainly useful in very large networks to:
- Reduce IBGP full-mesh requirements
- Limit BGP path visibility and state propagation
- Maintain policy granularity inside large ASes

They do *not* magically fix route convergence issues, nor are they a replacement for BGP route reflectors. Use with caution and only if you know exactly why you're deploying them.

## Syntax

Add the `bgp.confederation` plugin and definition in the topology file:

```yaml
---
plugin: [ bgp.confederation ]       # Enable BGP Confederation plugin
module: [ bgp ]                     # Load BGP module (required)

# Define BGP Confederation
bgp.confederation:
  65000:                            # External-facing AS number
    members: [ 65001, 65002 ]       # Internal confederation AS numbers
```
## Platform Support

The plugin implements BGP confederation for these devices:

| Operating system    | BGP Confederation |
|---------------------|:-----------------:|
| Arista EOS          |        ✅         |
| Cumulus NVUE 5.x    |        ✅         |
| Dell OS10           |        ✅         |
| FRR                 |        ✅         |

## New Attributes

The plugin defines a new global attribute: 

* **bgp.confederation** (dict) -- a mapping of external-facing AS numbers to internal members

Internally, the plugin adds a new type of BGP session **confed_ebgp** to account for the fact that federated AS peers are more like iBGP peers than eBGP (e.g., they typically exchange extended communities).
**bgp.sessions** settings for such peers are inherited from **ibgp** (and currently cannot be controlled separately)