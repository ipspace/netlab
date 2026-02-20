(dev-mpls-6pe)=
# MPLS 6PE Configuration Templates

This document describes how to create MPLS 6PE configuration templates for network devices supported by *netlab*.

MPLS 6PE (IPv6 over MPLS) is a sub-feature of the [MPLS module](dev-mpls). It enables IPv6 transport over an MPLS backbone using IPv4 BGP sessions with label distribution, avoiding the need for a separate IPv6 control plane.

## Enabling 6PE Support on a Device

To enable 6PE support on a device, add the boolean `mpls.6pe` feature flag to the device YAML file (`netsim/devices/<device>.yml`):

```yaml
mpls:
  6pe: true
```

The 6PE configuration template should be stored in the `netsim/ansible/templates/mpls/` directory (name `<platform>.6pe.j2`) or within the `netsim/ansible/templates/mpls/<platform>` directory (name: `6pe.j2`).

## Template Variables

The following variables are available in 6PE configuration templates:

### Node-Level Variables

| Variable | Type | Description |
|----------|------|-------------|
| `mpls.6pe` | list | Session types for 6PE (ibgp, ebgp) |
| `bgp.as` | int | BGP AS number |
| `bgp.neighbors` | list | BGP neighbors |

### BGP Neighbor Attributes

The MPLS module sets the `6pe` attribute on BGP neighbors when the 6PE address family should be activated:

| Attribute | Description |
|-----------|-------------|
| `n.6pe` | Boolean flag indicating 6PE should be enabled for this neighbor |
| `n.ipv4` | IPv4 address of the neighbor (used as transport for 6PE) |

Notes:

* 6PE uses IPv4 BGP sessions to transport IPv6 routes with MPLS labels
* The neighbor must have an IPv4 session (`ipv4` attribute) configured
* If both ends of a BGP session use 6PE, the IPv6 session is not needed and is removed automatically

## Template Examples

### Cisco IOS

```
!
router bgp {{ bgp.as }}
 address-family ipv6
!
{% for n in bgp.neighbors if n.ipv4 is defined and n['6pe']|default(False) %}
  neighbor {{ n.ipv4 }} activate
  neighbor {{ n.ipv4 }} send-label
{% endfor %}
```

Key points:
* Enable IPv6 address family within BGP
* Activate 6PE for neighbors that have the `6pe` attribute set
* Use `send-label` to enable MPLS label distribution for IPv6 routes

### Arista EOS

```
!
router bgp {{ bgp.as }}
 address-family ipv6
!
{% for n in bgp.neighbors if n.ipv4 is defined and n['6pe']|default(False) }}
  neighbor {{ n.ipv4 }} activate 6pe
{% endfor %}
!
! EOS requires 'ipv6 enable' on internal PE interfaces
{% for l in interfaces|default([]) if l.type != 'stub' and l.neighbors is defined and not (l.ipv6|default(False)) }}
interf {{ l.ifname }}
 ipv6 enable
{% endfor %}
```

Key points:
* Activate 6PE address family using the `activate 6pe` syntax
* Enable IPv6 on PE interfaces that don't already have IPv6 configured

## Constraints

The 6PE feature has the following constraints:

* Requires IPv4 address family in the BGP process
* Cannot be used together with IPv6 BGP Labeled Unicast (`mpls.bgp.ipv6`)
* Requires LDP or BGP-LU for IPv4 next hop label distribution

## Testing

Use the tests in the `tests/integration/mpls` directory when adding 6PE support to a new platform.
