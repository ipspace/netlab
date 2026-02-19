(dev-mpls-ldp)=
# MPLS LDP Configuration Templates

This document describes how to create or modify MPLS LDP configuration templates for network devices supported by *netlab*.

MPLS LDP (Label Distribution Protocol) is a sub-feature of the MPLS module. It is enabled alongside other MPLS features (BGP-LU, VPN, 6PE) but has its own configuration template.

## Enabling LDP Support on a Device

To enable LDP support on a device, add the `mpls.ldp` feature flag to the device YAML file (`netsim/devices/<device>.yml`):

```yaml
mpls:
  ldp: true
```

Some devices support additional LDP-related features:

```yaml
mpls:
  ldp: true
  bgp: true      # BGP Labeled Unicast
  vpn: true      # MPLS/VPN
  6pe: true      # 6PE (IPv6 over MPLS)
```

### Supported Platforms

The following platforms have LDP support enabled:

| Device | Device YAML | Template |
|--------|-------------|----------|
| Arista EOS | `mpls.ldp: true` | `eos.ldp.j2` |
| Cisco IOS | `mpls.ldp: true` | `ios.ldp.j2` |
| Cisco IOS-XR | `mpls.ldp: true` | (uses IOS template) |
| FRRouting | `mpls: [ ldpd ]` | `frr.ldp.j2` |
| Juniper Junos | `mpls.ldp: true` | `junos.ldp.j2` |
| Nokia SROS | `mpls.ldp: true` | `sros.ldp.j2` |
| Aruba CX | `mpls.ldp: true` | `arubacx.ldp.j2` |
| VyOS | `mpls.ldp: true` | `vyos.ldp.j2` |
| RouterOS | `mpls.ldp: true` | `routeros.ldp.j2` |
| SR Linux | `mpls.ldp: true` (7250 IXR only) | `srlinux.ldp.j2` |

## Template Architecture

The MPLS configuration uses a two-tier template structure:

### Main MPLS Template

The `<platform>.j2` template (e.g., `eos.j2`) includes LDP and other MPLS sub-feature templates:

```jinja2
{% if ldp is defined %}
{%   include 'eos.ldp.j2' +%}
{% endif %}
{% if mpls.bgp is defined %}
{%   include 'eos.bgp-lu.j2' +%}
{% endif %}
{% if mpls.vpn is defined %}
{%   include 'eos.mplsvpn.j2' +%}
{% endif %}
```

### LDP-Specific Template

The `<platform>.ldp.j2` template contains the actual LDP configuration commands.

## Template Variables

The following variables are available in LDP configuration templates:

### Node-Level Variables

| Variable | Type | Description |
|----------|------|-------------|
| `ldp.router_id` | string | LDP router ID (IPv4 address) |
| `ldp.explicit_null` | bool | Enable explicit null labels (default: False) |
| `ldp.af.ipv4` | bool | IPv4 address family enabled |
| `ldp.af.ipv6` | bool | IPv6 address family enabled (FRR only) |
| `loopback.ipv4` | IPv4 | Loopback IPv4 address |
| `loopback.ipv6` | IPv6 | Loopback IPv6 address (FRR) |

### Interface Variables

When iterating over interfaces, use this pattern to find LDP-enabled interfaces:

```jinja2
{% for l in interfaces if ('ldp' in l) and not l.ldp.passive %}
interface {{ l.ifname }}
  mpls ip
{% endfor %}
```

| Variable | Description |
|----------|-------------|
| `l.ifname` | Interface name |
| `l.ldp.passive` | Passive LDP interface (receives labels but does not advertise) |

## Template Examples

### Arista EOS

```jinja2
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
- Enable LDP on all non-passive interfaces

### Cisco IOS

```jinja2
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

```jinja2
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

### Juniper Junos

```jinja2
interfaces {
{% for l in interfaces if ('ldp' in l) and not l.ldp.passive %}
  {{ l.ifname }} {
    family mpls;
  }
{% endfor %}
}

protocols {
  mpls {
{% for l in interfaces if ('ldp' in l) and not l.ldp.passive %}
    interface {{ l.ifname }};
{% endfor %}
  }
  ldp {
{% if ldp.explicit_null|default(False) %}
    explicit-null;
{% endif %}
{% for l in interfaces if ('ldp' in l) and not l.ldp.passive %}
    interface {{ l.ifname }};
{% endfor %}
  }
}
```

### Nokia SROS

```julan
- path: system/mpls
  val:
   - path: admin-state
     val: enable
   - path: path-vector-limit
     val: 100

- path: router[router-name=Base]/ldp
   val:
    admin-state: enable
    implicit-null-label: {{ not ldp.explicit_null|default(False) }}
{%  for l in interfaces if ('ldp' in l) and not l.ldp.passive %}
    interface: {{ l.ifname }}
{%  endfor %}
{% if not ldp.igp_sync|default(True) %}
- path: router[router-name=Base]/ldp/sync-igp
    ldp-sync: False
{% endif %}
```

## Link/Interface Attributes

LDP can be enabled or disabled on individual interfaces using link attributes:

### `mpls.ldp` (link attribute)

```yaml
links:
- nodes: [router1, router2]
  mpls.ldp: true    # Enable LDP on this link
```

### `ldp.passive` (interface attribute)

Passive LDP interfaces receive label bindings but do not initiate LDP sessions:

```yaml
links:
- nodes: [router1, router2]
  router1:
    mpls.ldp: true
  router2:
    mpls.ldp: true
    ldp.passive: true   # router2 is passive
```

## Requirements and Dependencies

LDP has the following requirements:

1. **IPv4**: LDP requires IPv4 address family on the node
2. **IGP**: An IGP (OSPF, IS-IS, or EIGRP) must be running on the node
3. **Loopback**: LDP router ID is typically derived from the loopback interface

These requirements are validated in the Python transformation code (`netsim/modules/mpls.py`):

- `node_adjust_ldp()` checks for IPv4 address family
- `node_pre_transform()` verifies an IGP is present

## VRF/LDP CSC Support

LDP can be used within VRFs (LDP Carrier Supporting Carrier - CsC). This requires:

- Setting `mpls.ldp: true` on individual VRF interfaces
- Device support for MPLS CsC (checked via device features)

## Testing

When adding LDP support to a new platform:

1. Create a test topology with LDP enabled
2. Verify LDP adjacencies form between devices
3. Test `explicit_null` option
4. Test passive interface configuration
5. Test interoperability with other platforms

Example test topology:

```yaml
provider: libvirt

nodes:
  router1:
    device: eos
  router2:
    device: ios

module: [ mpls, ospf ]

mpls:
  ldp: true

links:
- router1-router2
```
