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

### 2. junos.j2 (line 10-14)

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

## Summary

**Total Issues Found:**
- BGP VRF templates: 4 problems
- OSPF VRF templates: 2 problems

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

