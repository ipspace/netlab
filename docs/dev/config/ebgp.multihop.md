(dev-config-ebgp-multihop)=
# Configuring EBGP Multihop

This document describes how to write configuration templates for the **ebgp.multihop** plugin. For a wider picture, please see the [contributing new devices](../devices.md) document.

**Notes:**

* The plugin configuration template should be stored in `netsim/extra/ebgp.multihop/<nos>.j2` where **nos** is the value of the **netlab_device_type** or **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](../devices.md#using-your-device-with-ansible-playbooks) for more details).
* The plugin augments existing BGP neighbor entries. Your template should only configure the multihop-specific parameters; all other BGP configuration is handled by the standard BGP template.
* All attributes described below are optional. Use `if sth is defined` checks in your Jinja2 templates.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(dev-ebgp-multihop-features)=
## Device Features

Add `features.bgp.multihop: true` to your device definition to indicate that the device supports EBGP multihop sessions. The `ebgp.multihop` plugin uses this flag to determine which devices it should configure.

(dev-ebgp-multihop-neighbor)=
## BGP Neighbor Attributes

The plugin adds the following attributes to relevant entries in the **bgp.neighbors** list (and the VRF equivalent **vrfs._vname_.bgp.neighbors**):

* **multihop** (int) -- The EBGP multihop TTL value. A value of **255** means "unlimited" (use the platform's maximum TTL or omit the count). Values below 255 should be configured explicitly.
* **\_source\_intf** (optional) -- The loopback interface from which the BGP session should originate. This attribute is a dictionary with:
  * **ifname** -- The interface name (e.g., `Loopback0`)
  * **ipv4** (optional) -- The IPv4 address assigned to the source interface
  * **ipv6** (optional) -- The IPv6 address assigned to the source interface

Use `n[af]` to get the neighbor's IP address (as in any BGP template), and add the multihop and update-source commands when the corresponding attributes are present.

(dev-ebgp-multihop-template)=
## Template Structure

The ebgp.multihop plugin template is called **after** the standard BGP template has already configured the BGP process and neighbors. It only needs to add the multihop-specific commands to the existing neighbor definitions.

The simplest approach is to define a macro and call it for every neighbor that has an IP address in the current address family:

```
{% macro ebgp_session(n,af) -%}
{%   if n.multihop is defined %}
  neighbor {{ n[af] }} ebgp-multihop {{ n.multihop if n.multihop < 255 else '' }}
{%   endif %}
{%   if n._source_intf is defined %}
  neighbor {{ n[af] }} update-source {{ n._source_intf.ifname }}
{%   endif %}
{%- endmacro %}
!
router bgp {{ bgp.as }}
{% for af in ['ipv4','ipv6'] %}
{%   for n in bgp.neighbors if n[af] is defined %}
{{     ebgp_session(n,af) -}}
{%   endfor %}
{% endfor %}
```

(dev-ebgp-multihop-vrf)=
## Configuring VRF BGP Instances

The plugin also handles multihop sessions within VRFs. Apply the same macro to each VRF's neighbor list. The exact structure varies by platform:

**FRRouting** (separate `router bgp` per VRF):

```
{% if vrfs is defined %}
{%   for vname,vdata in vrfs.items() if vdata.bgp is defined %}
router bgp {{ vdata.as|default(bgp.as) }} vrf {{ vname }}
{%     for af in ['ipv4','ipv6'] %}
{%       for n in vdata.bgp.neighbors if n[af] is defined %}
{{         ebgp_session(n,af) -}}
{%       endfor %}
{%     endfor %}
{%   endfor %}
{% endif %}
```

**Cisco IOS** (address-family VRF context):

```
{% if vrfs is defined %}
{%   for vname,vdata in vrfs.items() %}
{%     for af in ('ipv4','ipv6') if af in vdata.af|default({}) %}
 address-family {{ af }} vrf {{ vname }}
{%       for n in vdata.bgp.neighbors if n[af] is defined %}
{{         ebgp_session(n,af) -}}
{%       endfor %}
{%     endfor %}
{%   endfor %}
{% endif %}
```

**Arista EOS** (vrf sub-context within `router bgp`):

```
{% if vrfs is defined %}
{%   for vname,vdata in vrfs.items() if vdata.bgp is defined %}
 vrf {{ vname }}
{%     for af in ['ipv4','ipv6'] %}
{%       for n in vdata.bgp.neighbors if n[af] is defined %}
{{         ebgp_session(n,af) -}}
{%       endfor %}
{%     endfor %}
{%   endfor %}
{% endif %}
```

(dev-ebgp-multihop-tests)=
## Integration Tests

The integration tests for this plugin are in the `tests/integration/bgp.multihop/` directory:

* **01-global.yml** -- Dual-stack EBGP multihop sessions (IPv4 + IPv6 loopbacks)
* **02-vrf.yml** -- EBGP multihop sessions within VRFs using VRF loopbacks
* **x-01-global-ipv4.yml** -- IPv4-only variant of the global test
* **x-03-localas_ibgp.yml** -- EBGP multihop with a `local_as` configuration that converts the session to IBGP
