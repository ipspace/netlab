(dev-mpls-ldp)=
# MPLS LDP Configuration Templates

This document describes how to create or modify MPLS LDP configuration templates for network devices supported by *netlab*.

MPLS LDP (Label Distribution Protocol) is a sub-feature of the [MPLS module](mpls.md). It is enabled alongside other MPLS features (BGP-LU, VPN, 6PE) but has its own configuration template.

## Enabling LDP Support on a Device

To enable LDP support on a device, add the `mpls.ldp` feature flag to the device YAML file (`netsim/devices/<device>.yml`):

```yaml
mpls:
  ldp: true
```

The LDP configuration template should be stored in the `netsim/ansible/templates/mpls/` directory (name `<platform>.ldp.j2`) or within the `netsim/ansible/templates/mpls/<platform>` directory (name: `ldp.j2`)

## Template Variables

The following variables are available in LDP configuration templates:

### Node-Level Variables

| Variable | Type | Description |
|----------|------|-------------|
| `ldp.router_id` | string | LDP router ID (IPv4 address) |
| `ldp.explicit_null` | bool | Enable explicit null labels (default: False) |
| `ldp.af.ipv4` | bool | Enable LDP |
| `ldp.af.ipv6` | bool | Enable LDPv6 (optional, not tested) |

### Interface Variables

When iterating over interfaces, use this pattern to find LDP-enabled interfaces:

```
{% for l in interfaces if ('ldp' in l) and not l.ldp.passive %}
interface {{ l.ifname }}
  mpls ip
{% endfor %}
```

| Variable | Description |
|----------|-------------|
| `l.ifname` | Interface name |
| `l.ldp.passive` | LDP is not enabled on this interface |

```{tip}
There is no **‌ldp.passive** interface attribute. The **‌ldp.passive** attribute is set internally on stub links and links with **‌role** set to **‌passive**. For LDP, **‌passive** is functionally identical to *‌do not run LDP on this interface*.
```

## Template Examples

### Arista EOS

```
!
mpls ip
mpls icmp ttl-exceeded tunneling
!
mpls ldp
  router-id {{ ldp.router_id }}
  transport-address interface Loopback0
  interface disabled default
  no shutdown
{% if ldp.explicit_null|default(False) %}
  label local-termination explicit-null
{% endif %}
!
interface Loopback0
  mpls ldp interface
!
{% for l in interfaces if ('ldp' in l) and not l.ldp.passive %}
interface {{ l.ifname }}
  mpls ip
  mpls ldp interface
{% endfor %}
```

Key points:
- Global `mpls ip` enables MPLS forwarding
- LDP router ID and transport address (usually loopback)
- Enable LDP on loopback interface
- Enable LDP on all relevant interfaces (interface must have **ldp** dictionary, but should not have **ldp.passive** set to True)

### Cisco IOS

```
!
mpls ldp router-id Loopback0
mpls ldp logging neighbor-changes
{% if ldp.explicit_null|default(False) %}
mpls ldp explicit-null
{% endif %}
!
{% for l in interfaces if ('ldp' in l) and not l.ldp.passive %}
interface {{ l.ifname }}
 mpls ip
{% endfor %}
!
```

### FRRouting

```
!
mpls ldp
  router-id {{ ldp.router_id }}
{% if not 'ipv6' in loopback %}
  dual-stack transport-connection prefer ipv4
{% endif %}
{% for af in ['ipv4','ipv6'] if ldp.af[af] is defined %}
  address-family {{ af }}
{%   if loopback[af] is defined %}
    discovery transport-address {{ loopback[af]|ansible.utils.ipaddr('address') }}
{%   endif %}
{%   if ldp.explicit_null|default(False) %}
    label local advertise explicit-null
{%   endif %}
{%   for l in interfaces if ('ldp' in l) and (af in l) and not l.ldp.passive %}
    interface {{ l.ifname }}
    exit
{%   endfor %}
  exit
{% endfor %}
!
```

FRR supports:
- IPv4 and IPv6 address families
- Dual-stack transport connections
- Per-AF transport addresses

## VRF/LDP CSC Support (WIP)

LDP can be used within VRFs (LDP Carrier Supporting Carrier - CsC). This requires:

- Setting `mpls.ldp: true` on individual VRF interfaces
- Device support for MPLS CsC (checked via device features)

## Testing

Use these integration tests (in `tests/integration/mpls` directory) when adding LDP support to a new platform:

* `01-ldp-p` -- LDP functionality on P-device (establishing LDP adjacency, exchanging labels, building working LSPs)
* `02-ldp-pe` -- LDP functionality on PE-device (use LDP to assign labels to BGP next hops)
