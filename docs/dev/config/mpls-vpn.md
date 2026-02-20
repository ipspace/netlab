(dev-mpls-vpn)=
# MPLS/VPN Configuration Templates

This document describes how to create or modify MPLS/VPN (L3VPN) configuration templates for network devices supported by *netlab*.

MPLS/VPN is a sub-feature of the [MPLS module](mpls.md). It requires the [VRF module](module-vrf) to be enabled and uses BGP VPN address families to exchange routing information between PE routers.

## Enabling MPLS/VPN Support on a Device

To enable VPN support on a device, add the `mpls.vpn` feature flag to the device YAML file (`netsim/devices/<device>.yml`):

```yaml
mpls:
  vpn: true
```

The `mpls.vpn` parameter supports multiple formats:

* **Boolean**: Enables VPN for both IPv4 and IPv6 over IBGP sessions
* **Dictionary**: Enables MPLS/VPN only for specified address families. Use this when the device does not support VPNv6, for example:

  ```yaml
  mpls:
    vpn:
      ipv4: true
  ```

The MPLS/VPN configuration template should be stored in the `netsim/ansible/templates/mpls/` directory (name `<platform>.mplsvpn.j2`) or within the `netsim/ansible/templates/mpls/<platform>` directory (name: `mplsvpn.j2`)

It usually enables BGP VPNv4/VPNv6 address families and activates them on BGP neighbors that have been configured for VPN AF exchange. The VRF configuration and route redistribution are done within the VRF configuration template.

## Template Variables

The following variables are available for use in VPN configuration templates:

| Variable | Type | Description |
|----------|------|-------------|
| `mpls.vpn` | dict | VPN settings per address family |
| `mpls.vpn.ipv4` | list | Session types for VPNv4 (ibgp, ebgp) |
| `mpls.vpn.ipv6` | list | Session types for VPNv6 (ibgp, ebgp) |
| `bgp.as` | int | BGP AS number |
| `bgp.neighbors` | list | BGP neighbors (each neighbor may have `vpnv4` or `vpnv6` set) |

### BGP Neighbor Attributes

The MPLS module sets `vpnv4` or `vpnv6` attributes on BGP neighbors when the VPN address family should be activated with that neighbor:

| Attribute | Description |
|-----------|-------------|
| `n.vpnv4` | IPv4 address to use for VPNv4 session |
| `n.vpnv6` | IPv4 address to use for VPNv6 session (VPNv6 uses IPv4 transport) |

Notes:

* Consider other BGP neighbor parameters (**rr_client** or **type**) to configure additional BGP neighbor parameters within the VPNv4/VPNv6 address families.
* Enable extended community propagation with VPNv4 and VPNv6 address families if needed. MPLS/VPN won't work without them anyway.

## Template Examples

### Arista EOS

```
!
router bgp {{ bgp.as }}

{% for af in ['ipv4','ipv6'] if mpls.vpn[af] is defined %}
{%   set vpnaf = 'vpn' + af.replace('ip','') %}
{%   for n in bgp.neighbors if n[vpnaf] is defined %}
  neighbor {{ n[vpnaf] }} send-community add extended
{%   endfor %}
!
  address-family vpn-{{ af }}
!
{%   for n in bgp.neighbors if n[vpnaf] is defined %}
   neighbor {{ n[vpnaf] }} activate
{%   endfor %}
  exit
{% endfor %}
```

Key points:
- Enable extended community format with `send-community add extended`
- Activate VPN address family for each neighbor that has the vpnv4/vpnv6 attribute set
- Use `vpn-ipv4` and `vpn-ipv6` address family names

### Cisco IOS

```
!
router bgp {{ bgp.as }}
{% for af in ['ipv4','ipv6'] if mpls.vpn[af] is defined %}
{%   set vpnaf = 'vpn' + af.replace('ip','') %}
 address-family {{ vpnaf }}
!
{%   for n in bgp.neighbors if n[vpnaf] is defined %}
   neighbor {{ n[vpnaf] }} activate
   neighbor {{ n[vpnaf] }} send-community both
{%   endfor %}
{% endfor %}
```

Key points:
- Use `vpnv4` and `vpnv6` address family names
- Enable both standard and extended communities with `send-community both`

### FRRouting

```
!
router bgp {{ bgp.as }}
{% for af in ['ipv4','ipv6'] if mpls.vpn[af] is defined %}
{%   set vpnaf = 'vpn' + af.replace('ip','') %}
 address-family {{ af }} vpn
!
{%   for n in bgp.neighbors if n[vpnaf] is defined %}
   neighbor {{ n[vpnaf] }} activate
   neighbor {{ n[vpnaf] }} send-community both
{%     if n.type == 'ibgp' %}
   neighbor {{ n[vpnaf] }} next-hop-self
{%     endif %}
{%   endfor %}
{% endfor %}
```

Key points:
- FRR uses `ipv4 vpn` and `ipv6 vpn` address family syntax
- Include `next-hop-self` for IBGP neighbors to ensure proper next-hop resolution in the VPN

## Testing

Use integration tests in the `tests/integration/mpls` directory when adding MPLS/VPN configuration templates for a new platform.
