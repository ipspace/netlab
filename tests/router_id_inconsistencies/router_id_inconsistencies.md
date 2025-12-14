# Router ID Handling Inconsistencies in VRF Templates

This document identifies inconsistencies in how router IDs are handled in VRF templates across different device types.

## Standard Pattern

The correct pattern for handling router IDs in VRF contexts should be:

- **BGP**: `vdata.bgp.router_id|default(bgp.router_id)`
- **OSPF**: `vdata.ospf.router_id|default(ospf.router_id)`

This pattern allows VRF-specific router_id to override the global router_id, but falls back to the global router_id if the VRF-specific one is not set.

## BGP VRF Template Issues

### 1. routeros7.bgp.j2 (line 14-15)

**Current:**
```jinja2
{% if bgp.router_id is defined %}
/routing/bgp/template set vrf_{{ vname }} router-id={{ bgp.router_id }}
{% endif %}
```

**Problem:** Uses `bgp.router_id` directly without checking `vdata.bgp.router_id` first. This means VRF-specific router IDs are ignored.

**Should be:**
```jinja2
{% if vdata.bgp.router_id is defined or bgp.router_id is defined %}
/routing/bgp/template set vrf_{{ vname }} router-id={{ vdata.bgp.router_id|default(bgp.router_id) }}
{% endif %}
```

### 2. iosxr.bgp.j2 (line 18-19)

**Current:**
```jinja2
{% if vdata.bgp.router_id is defined %}
  bgp router-id {{ vdata.bgp.router_id }}
{% endif %}
```

**Problem:** Only checks for VRF-specific router_id, doesn't fall back to global `bgp.router_id`.

**Should be:**
```jinja2
{% if vdata.bgp.router_id is defined or bgp.router_id is defined %}
  bgp router-id {{ vdata.bgp.router_id|default(bgp.router_id) }}
{% endif %}
```

### 3. nxos.bgp.j2 (line 10-11)

**Current:**
```jinja2
{%   if bgp.router_id is defined %}
    router-id {{ bgp.router_id }}
{%   endif %}
```

**Problem:** Uses `bgp.router_id` directly without checking `vdata.bgp.router_id` first.

**Should be:**
```jinja2
{%   if vdata.bgp.router_id is defined or bgp.router_id is defined %}
    router-id {{ vdata.bgp.router_id|default(bgp.router_id) }}
{%   endif %}
```

### 4. junos.bgp.j2 (line 61-62)

**Current:**
```jinja2
{%   if bgp.router_id is defined %}
      router-id {{ vdata.bgp.router_id|default(bgp.router_id) }}
{%   endif %}
```

**Problem:** The outer check `{% if bgp.router_id is defined %}` prevents output when only `vdata.bgp.router_id` is set. If `bgp.router_id` is not defined but `vdata.bgp.router_id` is defined, nothing will be output.

**Should be:**
```jinja2
{%   if vdata.bgp.router_id is defined or bgp.router_id is defined %}
      router-id {{ vdata.bgp.router_id|default(bgp.router_id) }}
{%   endif %}
```

## OSPF VRF Template Issues

### 1. nxos.ospfv2-vrf.j2 (line 20-21)

**Current:**
```jinja2
{% if vdata.ospf.router_id is defined %}
  router-id {{ vdata.ospf.router_id }}
{% endif %}
```

**Problem:** Only checks for VRF-specific router_id, doesn't fall back to global `ospf.router_id`.

**Should be:**
```jinja2
{% if vdata.ospf.router_id is defined or ospf.router_id is defined %}
  router-id {{ vdata.ospf.router_id|default(ospf.router_id) }}
{% endif %}
```

### 2. vyos.ospfv2-vrf.j2 (line 3-4)

**Current:**
```jinja2
{% if vdata.ospf.router_id is defined or ospf.router_id is defined %}
set protocols ospf parameters router-id {{ vdata.ospf.router_id|default(ospf.router_id) }}
{% endif %}
```

**Status:** ✅ **This is actually correct!** The check ensures output only when at least one router_id exists, and the `default()` filter correctly handles the fallback. This pattern is acceptable, though slightly verbose.

**Note:** This could be simplified for consistency, but it's not incorrect.

### 3. vyos.ospfv3-vrf.j2 (line 3-4)

**Current:**
```jinja2
{% if vdata.ospf.router_id is defined or ospf.router_id is defined %}
set protocols ospfv3 parameters router-id {{ vdata.ospf.router_id|default(ospf.router_id) }}
{% endif %}
```

**Status:** ✅ **This is actually correct!** Same pattern as ospfv2-vrf.j2 - acceptable.

### 4. junos.j2 (line 10-14)

**Current:**
```jinja2
{% if vdata.ospf.router_id is defined %}
routing-instances {
  {{ vname }} {
    routing-options {
      router-id {{ vdata.ospf.router_id }}
    }
```

**Problem:** Only checks for VRF-specific router_id, doesn't fall back to global `ospf.router_id`.

**Should be:**
```jinja2
{% if vdata.ospf.router_id is defined or ospf.router_id is defined %}
routing-instances {
  {{ vname }} {
    routing-options {
      router-id {{ vdata.ospf.router_id|default(ospf.router_id) }}
    }
```

## Templates Using Correct Pattern

These templates correctly use the standard pattern:

### BGP VRF Templates:
- `vrf/eos.bgp.j2`: `router-id {{ vdata.bgp.router_id|default(bgp.router_id) }}`
- `vrf/ios.bgp.j2`: `bgp router-id {{ vdata.bgp.router_id|default(bgp.router_id) }}`
- `vrf/frr.bgp.j2`: `bgp router-id {{ vdata.bgp.router_id|default(bgp.router_id) }}`
- `vrf/vyos.bgp.j2`: `set protocols bgp parameters router-id {{ vdata.bgp.router_id|default(bgp.router_id) }}`
- `vrf/arubacx.bgp.j2`: `bgp router-id {{ vdata.bgp.router_id|default(bgp.router_id) }}`
- `vrf/dellos10.bgp.j2`: `router-id {{ vdata.bgp.router_id|default(bgp.router_id) }}`
- `vrf/srlinux.j2`: Uses macro with `vdata.bgp.router_id|default(bgp.router_id)`
- `vrf/sros.j2`: `router-id: {{ vdata.bgp.router_id|default(bgp.router_id if bgp is defined else loopback.ipv4|ipaddr('address')) }}`

### OSPF VRF Templates:
- `vrf/dellos10.ospfv2-vrf.j2`: `router-id {{ vdata.ospf.router_id|default(ospf.router_id) }}`
- `vrf/arubacx.ospfv2-vrf.j2`: `router-id {{ vdata.ospf.router_id|default(ospf.router_id) }}`
- `vrf/arubacx.ospfv3-vrf.j2`: `router-id {{ vdata.ospf.router_id|default(ospf.router_id) }}`
- `vrf/routeros7.ospfv2-vrf.j2`: `{% set ospf_router_id = vdata.ospf.router_id|default(ospf.router_id) %}`
- `vrf/routeros.ospfv2-vrf.j2`: `router-id={{ vdata.ospf.router_id|default(ospf.router_id) }}`

## Summary

**Total Issues Found:**
- BGP VRF templates: 4 real problems
- OSPF VRF templates: 2 real problems (2 templates are correct but verbose)

**Impact:**
- Templates that don't check `vdata.bgp.router_id` or `vdata.ospf.router_id` first will ignore VRF-specific router IDs
- Templates that don't fall back to global router_id may not set a router ID when only the global one is configured
- Redundant checks add unnecessary complexity

**Recommendation:**
Standardize all VRF templates to use the pattern:
```jinja2
{% if vdata.bgp.router_id is defined or bgp.router_id is defined %}
  router-id {{ vdata.bgp.router_id|default(bgp.router_id) }}
{% endif %}
```

Or, if the router-id is always required (device will use a default), simply:
```jinja2
router-id {{ vdata.bgp.router_id|default(bgp.router_id) }}
```

