(dev-config-srv6)=
# Configuring SRv6

This document describes the device data model parameters one should consider when creating an [SRv6](module-srv6) device configuration template. For a wider picture, please see the [contributing new devices](../devices.md) document.

The configuration template (in Jinja2 format) should be stored in the `netsim/ansible/templates/srv6/` directory. The template file name is derived from the `netlab_device_type` or `ansible_network_os` variable (see [](dev-config-bgp) for details on how the platform name is used).

```{tip}
The `<platform>` is the value of the `netlab_device_type` or `ansible_network_os` variable.
```

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Device Features

Add the following **features.srv6** entries to a device YAML file (`netsim/devices/<device>.yml`) to indicate which SRv6 features the platform supports:

* **isis** -- device supports SRv6 with IS-IS
* **ospf** -- device supports SRv6 with OSPFv3
* **bgp** -- device supports BGP v4/v6 overlay over SRv6 (end.dt4/end.dt6)
* **vpn** -- device supports BGP L3VPN v4/v6 over SRv6

## Node Attributes

The `srv6` node dictionary is always present on nodes that have the `srv6` module enabled. It contains the following attributes after transformation:

### srv6.locator

An IPv6 prefix in CIDR notation (e.g., `5f00:0:1::/48`), specified in lab topology or automatically allocated per-node from the SRv6 locator address pool (default `5F00::/16`, based on the IANA-reserved range in [RFC 9602](https://datatracker.ietf.org/doc/html/rfc9602)).

Templates typically use `srv6.locator` to configure the SRv6 locator prefix:

```
locator {{ inventory_hostname }}
  prefix {{ srv6.locator }}
```

### srv6.igp

A list of IGP protocol names (e.g., `['isis']`) over which SRv6 should be signalled. The default is `['isis']`. Valid values are `isis` and `ospf`.

Use `if 'isis' in srv6.igp` (or `'ospf' in srv6.igp`) to conditionally enable SRv6 under an IGP:

```
{% if 'isis' in srv6.igp %}
router isis {{ isis.instance }}
  segment-routing srv6
    locator {{ inventory_hostname }}
{% endif %}
```

### srv6.bgp

An optional dictionary with keys `ipv4` and/or `ipv6`, each containing a list of BGP neighbor types that should use SRv6 as the transport for the plain IPv4 or IPv6 unicast address family (end.dt4/end.dt6, *not* VPN).

`srv6.bgp` is absent when the feature is disabled.

Example:

```
{% if srv6.bgp is defined %}
{%   for af in ['ipv4','ipv6'] if af in srv6.bgp %}
  family {{ af }}
    locator {{ inventory_hostname }}
{%   endfor %}
{% endif %}
```

### srv6.vpn

A dictionary with keys `ipv4` and/or `ipv6`, each containing a list of BGP neighbor types for which BGP L3VPN routes should be carried over SRv6 (end.dt4-vrf/end.dt6-vrf).

The structure and boolean-expansion rules are identical to `srv6.bgp`. `srv6.vpn` is absent when L3VPN is disabled.

### srv6.transit_only

A boolean flag (`True`/`False`). When `True`, the node acts as a transit-only SRv6 node — it forwards SRv6 traffic but does not need to allocate FPE resources or end.dt SIDs for originating/terminating traffic. Default is `False`.

```
{% if not srv6.transit_only|default(False) %}
  termination-fpe: [2]
{% endif %}
```

## Loopback IPv6 Address

`loopback.ipv6` is always present on SRv6 nodes (enforced by `node_post_transform`). It may be user-defined, assigned from the `loopback` topology pool, or automatically assigned as the first host address in `srv6.locator` (when `srv6.allocate_loopback: True`).

Templates must use `loopback.ipv6` as the SRv6 source address:

```
source-address {{ loopback.ipv6 | ansible.utils.ipaddr('address') }}
```

## BGP Neighbor Attributes

The `srv6` module modifies the `bgp.neighbors` list during `node_post_transform`. For each BGP neighbor that...

* has an `ipv6` transport address
* has no `ipv4` transport address,
* is listed in `srv6.bgp.ipv4` or `srv6.vpn.ipv4` (i.e., IPv4 AF is carried over an IPv6 session)

...the module adds:

* **extended_nexthop** (`True`) — signals that the BGP session requires extended next-hop encoding (RFC 8950) to carry IPv4 prefixes over an IPv6 transport session.

Templates could check for this attribute to conditionally enable extended next-hop negotiation:

```
{% for n in bgp.neighbors|default([]) if n.ipv6 is defined %}
{%   if n.extended_nexthop is defined %}
  neighbor {{ n.ipv6 }} capability extended-nexthop
{%   endif %}
{% endfor %}
```

## Interface Attributes

The `srv6` module does not add any per-interface attributes. Templates that need SRv6 interface-level configuration (e.g., end.x SIDs) typically iterate over interfaces that have IS-IS or OSPF enabled:

```
{% set srv6_interfaces = interfaces | selectattr('isis','defined') | list %}
```

## Template Architecture

Complex platforms may split SRv6 configuration into a main template and a conditionally-included BGP sub-template. The main template handles locator declaration and IGP integration; the BGP sub-template handles the BGP overlay and VPN configuration.

**Example** (`frr.j2` main template, simplified):

```
segment-routing
 srv6
  encapsulation
   source-address {{ loopback.ipv6 | ansible.utils.ipaddr('address') }}
  locators
   locator {{ inventory_hostname }}
    prefix {{ srv6.locator }}

{% if 'isis' in srv6.igp|default([]) and isis.instance is defined %}
router isis {{ isis.instance }}
 segment-routing srv6
   locator {{ inventory_hostname }}
{% endif %}

{% if srv6.vpn is defined and bgp.as is defined %}
{%   include "frr.bgp.j2" %}
{% endif %}
```

**Example** (`frr.bgp.j2` BGP sub-template, simplified):

```
router bgp {{ bgp.as }}
 segment-routing srv6
  locator {{ inventory_hostname }}

{% if srv6.vpn is defined %}
{%   for n in bgp.neighbors|default([]) if n.ipv6 is defined %}
{%     if n.extended_nexthop is defined %}
 neighbor {{ n.ipv6 }} capability extended-nexthop
{%     endif %}
{%     for af in ['ipv4','ipv6'] if n.type in srv6.vpn.get(af,[]) %}
 address-family {{ af }} vpn
  neighbor {{ n.ipv6 }} activate
{%     endfor %}
{%   endfor %}
{% endif %}
```

**Example** (`sros.j2`, Nokia SR-OS — gNMI/YANG path style):

```
{% set srv6_interfaces = interfaces | selectattr('isis','defined') | list %}
updates:
- path: configure/router[router-name=Base]/segment-routing/segment-routing-v6
  val:
   locator:
   - locator-name: JvB
     prefix:
      ip-prefix: {{ srv6.locator }}
{%   if not srv6.transit_only|default(False) %}
     termination-fpe: [2]
{%   endif %}

{% if 'isis' in srv6.igp %}
- path: configure/router[router-name=Base]/isis[isis-instance=0]
  val:
   segment-routing-v6:
    admin-state: enable
    locator:
    - locator-name: JvB
{% endif %}
```

## Integration Tests

The integration tests for the SRv6 module are in the `tests/integration/srv6/` directory:

* `02-isis-ipv4-bgp-vpn.yml` — PE router running IS-IS + BGP L3VPN (`srv6.vpn.ipv4: True`) over an IPv6-only SRv6 core, with VRFs attached; validates end-to-end L3VPN reachability.
* `12-isis-ipv6-bgp-vpn.yml` — Similar scenario with IPv6 L3VPN overlay.
* `x-01-isis-ipv4-bgp.yml` — PE router running IS-IS + BGP (`srv6.bgp.ipv4: True`) with `allocate_loopback: True`, carrying IPv4 over an IPv6-only SRv6 core (4PE scenario).
* `x-11-isis-ipv6-bgp.yml` — Similar scenario with IPv6 BGP overlay.
