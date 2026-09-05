(dev-config-bgp-session)=
# Configuring BGP Sessions

This document describes how to write configuration templates for the **bgp.session** plugin. For a wider picture, please see the [contributing new devices](../devices.md) and [developing plugins](../plugins.md) documents.

The **bgp.session** plugin implements numerous BGP session attributes (MD5 and TCP-AO passwords, GTSM, timers, BFD, passive peers, default route origination, AS-path manipulation, graceful restart, and route servers). It applies the attributes specified as global, node, link, or interface parameters to individual **bgp.neighbors** entries, so your configuration template only has to read neighbor attributes -- there is no need to re-evaluate the node- or interface-level data.

**Notes:**

* The plugin configuration template should be stored in `netsim/extra/bgp.session/<nos>.j2` where **nos** is the value of the **netlab_device_type** or **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](../devices.md#using-your-device-with-ansible-playbooks) for more details).
* The plugin adds `bgp.session` to the node **config** list for every node using one or more of its attributes. The configuration snippet is deployed after the standard BGP configuration template.
* The plugin configuration template should only configure the BGP session attributes described in this document; all other BGP configuration (BGP process, neighbors, address families, prefix origination) is handled by the standard BGP template (see [](dev-config-bgp)).
* Some devices (FortiOS) and daemons (BIRD) render the session attributes inside the standard BGP template. Their `bgp.session` templates (for example, `fortios.j2`) are empty.
* All attributes described below are optional. In your Jinja2 templates, guard access to them with `if <attribute> is defined` or `if <attribute>|default(False)` checks.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(dev-bgp-session-features)=
## Device Features

Add the following **features.bgp** [device features](dev-device-features) to your device definition to indicate that the device supports the corresponding BGP session attribute. The plugin checks these features whenever an attribute is applied to a neighbor and aborts the transformation if the device does not support the attribute.

* **allowas_in** -- device supports the **allowas-in** per-neighbor parameter
* **as_override** -- device supports the **as-override** per-neighbor parameter
* **bfd** -- device can run BFD on BGP sessions
* **default_originate** -- device can originate a default route toward a neighbor. Set it to the string **static** if the device has to originate a default route via a floating discard static route (for example, BIRD) -- see [](dev-bgp-session-default-route)
* **description** -- device supports per-neighbor descriptions
* **gr** -- device supports BGP graceful restart
* **gtsm** -- device supports the Generic TTL Security Mechanism
* **passive** -- device supports passive BGP sessions
* **password** -- device supports MD5 BGP passwords
* **remove_private_as** -- device supports private AS removal. Use a dictionary with a **valid** list to specify the supported values (`on`, `all`, `replace`, `ingress`, `ingress-all`, `ingress-replace`), for example:

  ```yaml
  features.bgp.remove_private_as.valid: [ 'on', all, replace ]
  ```

* **rs** -- device can act as a BGP route server
* **rs_client** -- device can be a BGP route server client (accept EBGP sessions with an unexpected first AS)
* **tcp_ao** -- device supports TCP-AO. Some platforms support TCP-AO only on selected providers, in which case the value is a list of provider names (for example, `tcp_ao: [ libvirt, external ]` on Arista EOS)
* **timers** -- device supports per-neighbor BGP keepalive/hold timers

(dev-bgp-session-node)=
## Node Attributes

The plugin sets (or populates) the following attributes in the **bgp** dictionary of nodes using the plugin:

* **bgp.gr** (optional) -- node-level BGP graceful restart parameters: a dictionary with **state** (`enable`, `disable`, or `helper`), **restart_time**, and **stalepath_time**. The same dictionary can be present in VRF data (**vrfs._vname_.bgp.gr**) as the node-level parameters are *not* applied to VRF BGP instances.
* **bgp.rs_client** (optional) -- set to *True* when the node has an EBGP session with a BGP route server. The configuration template has to disable the enforcement of the first AS on the BGP process (for example, `no bgp enforce-first-as` on Cisco IOS).
* **bgp._session_clear** (optional) -- a list of neighbor IP addresses (from relevant address families) that trigger the need to clear BGP sessions after the configuration is applied. The list is kept in the node **bgp** dictionary for global sessions and in **vrfs._vname_.bgp._session_clear** for VRF sessions. Use it to issue a `clear bgp ...` command toward the listed peers (the sample templates reset all sessions).
* **bgp._ao_secrets** (optional) -- a deduplicated list of TCP-AO passwords, used by templates that collect the TCP-AO secrets in global shared-secret management profiles (for example, Arista EOS). Iterate over the list to create the profiles and use `bgp._ao_secrets.index(n.password) + 1` to find the profile of a neighbor.
* **bgp._ao_algo_secrets** (optional) -- a deduplicated list of `algorithm:password` strings, used by templates that configure TCP-AO key chains (for example, Cisco IOS/IOS XR). Iterate over the list to create the key chains; the neighbor references a key chain with `bgp._ao_algo_secrets.index(n.tcp_ao + ":" + n.password) + 1`.
* The node **config** list gains a **bgp.session** entry.

(dev-bgp-session-neighbor)=
## BGP Neighbor Attributes

The plugin augments the relevant entries of the **bgp.neighbors** list (and the VRF equivalent **vrfs._vname_.bgp.neighbors**). A neighbor gets the attributes that were specified as node, link, or interface parameters and that are supported by the device. The following attributes can be present (use `if <attribute> is defined` or `|default(False)` guards):

* **password** (str) -- MD5 password, or the TCP-AO secret when **tcp_ao** is also set
* **tcp_ao** (str) -- the TCP-AO algorithm to use (`aes-128-cmac` or `hmac-sha-1`). A neighbor with **tcp_ao** always carries **password** as well; the plugin rejects TCP-AO neighbors without a password
* **gtsm** (int) -- the GTSM maximum hop count
* **passive** (bool) -- the session is passive
* **timers** (dict) -- BGP session timers with optional **keepalive**, **hold**, and **min_hold** fields
* **bfd** (bool) -- enable BFD on the BGP session (requires the **bfd** module on the node)
* **description** (str) -- neighbor description (usually rendered as `neighbor <peer> description <n.description>`)
* **default_originate** (bool) -- originate a default route toward the neighbor (see [](dev-bgp-session-default-route))
* **allowas_in** (int) -- allow that many occurrences of the local AS in the incoming AS path
* **as_override** (bool) -- replace the peer AS in outgoing updates
* **remove_private_as** (list) -- a list of private AS removal keywords (`on`, `all`, `replace`, `ingress`, `ingress-all`, `ingress-replace`) -- configure only the keywords supported by your device (see [](dev-bgp-session-features))
* **gr** (str) -- per-neighbor graceful restart state (`enable`, `disable`, or `helper`). Note that this is a *string* -- the node- and VRF-level graceful restart parameters are dictionaries in **bgp.gr**
* **rs** (bool) -- present on route server side: the neighbor is a route server client. Configure the route server behavior (for example, `neighbor <peer> route-server-client`) when this attribute is set
* **rs_client** (bool) -- present on client side: the neighbor is a route server (see [](dev-bgp-session-rs))

The plugin applies the session attributes to EBGP neighbors (all of them when the attribute is a node/global parameter, or the neighbors on the matching link/interface). IBGP neighbors inherit only the global/node attributes, and only when `bgp.session.apply.ibgp` is specified -- by default, the plugin does not apply the attributes to IBGP sessions.

**Important:** the **gr** attribute is applied to neighbors only from the interface/link BGP data -- node-level **bgp.gr** is never copied onto the neighbors; it stays in the **bgp.gr** dictionary.

(dev-bgp-session-default-route)=
## Default Route Origination

When the **default_originate** attribute is set on a neighbor and the device feature `features.bgp.default_originate` is the string **static**, the plugin adds floating *discard* static routes (`0.0.0.0/0` for IPv4 and `::/0` for IPv6) to the node **routing.static** list. The routes are added only when no user-specified default route matching the address family exists, and carry the **vrf** attribute when the default is originated toward a VRF neighbor:

```
node.routing.static:
- floating: true
  ipv4: 0.0.0.0/0          # or ipv6: ::/0
  nexthop:
    discard: true
  vrf: <vrf-name>          # only for VRF neighbors
```

The plugin also appends **routing** to the node's **module** list, so your device has to support the **routing** module and static routes to originate BGP defaults this way.

(dev-bgp-session-template)=
## Template Structure

The plugin template is applied **after** the standard BGP template has already configured the BGP process and the neighbors. Split the session attributes into two groups and configure them with two macros:

* **Session parameters** (outside the address families) -- usually **password**, **tcp_ao**, **gtsm**, **timers**, **bfd**, **passive**, **rs_client**
* **Address-family parameters** -- usually **default_originate**, **allowas_in**, **as_override**, **remove_private_as**, **gr**, **rs**

The sample macros are taken from the FRRouting template. The session macro handles both numbered and unnumbered (**local_if**) neighbors. Note that unnumbered neighbors might have **ipv4**/**ipv6** set to *True* instead of a string, so inspect the address with `is string` before using it as the peer:

```
{% macro ebgp_session(n,af) -%}
{%   set peer = n[af] if n[af] is string else n.local_if|default('?') %}
{%   if n.password is defined %}
  neighbor {{ peer }} password {{ n.password }}
{%   endif %}
{%   if n.gtsm is defined %}
  neighbor {{ peer }} ttl-security hops {{ n.gtsm }}
{%   endif %}
{%   if n.timers is defined %}
  neighbor {{ peer }} timers {{ n.timers.keepalive|default(60) }} {{ n.timers.hold|default(180) }}
{%   endif %}
{%   if n.bfd|default(False) %}
  neighbor {{ peer }} bfd
{%   endif %}
{%   if n.passive|default(False) %}
  neighbor {{ peer }} passive
{%   endif %}
{%   if n.rs_client|default(False) %}
  no neighbor {{ peer }} enforce-first-as
{%   endif %}
{%- endmacro %}

{% macro ebgp_neighbor(n,af) -%}
{%   set peer = n[af] if n[af] is string else n.local_if|default('?') %}
{%   if n.allowas_in|default(False) %}
  neighbor {{ peer }} allowas-in {{ n.allowas_in }}
{%   endif %}
{%   if n.as_override|default(False) %}
  neighbor {{ peer }} as-override
{%   endif %}
{%   if n.default_originate|default(False) %}
  neighbor {{ peer }} default-originate
{%   endif %}
{%   if n.remove_private_as|default([]) %}
{%     set rpa = { 'on': '', 'replace': 'all replace-AS', 'all': 'all' } %}
{%     for rpo in n.remove_private_as if rpo in rpa %}
  neighbor {{ peer }} remove-private-AS {{ rpa[rpo] }}
{%     endfor %}
{%   endif %}
{%   if n.rs|default(False) %}
  neighbor {{ peer }} route-server-client
{%   endif %}
{%   if n.gr is defined %}
  neighbor {{ peer }} graceful-restart{{ "-"+n.gr if n.gr != 'enable' else '' }}
{%   endif %}
{%- endmacro %}
```

Configure the node-level graceful restart parameters (**bgp.gr** dictionary) before iterating over the neighbors:

```
{% macro bgp_gr(bgp) %}
{%   if bgp.gr.restart_time is defined %}
  bgp graceful-restart restart-time {{ bgp.gr.restart_time }}
{%   endif %}
{%   if bgp.gr.stalepath_time is defined %}
  bgp graceful-restart stalepath-time {{ bgp.gr.stalepath_time }}
{%   endif %}
{%   set gr_state = bgp.gr.state %}
{%   if gr_state == 'disable' %}
  bgp graceful-restart-disable
{%   endif %}
{%   if gr_state == 'enable' %}
  bgp graceful-restart
{%   endif %}
{% endmacro %}

router bgp {{ bgp.as }}
{% if bgp.gr is defined %}
{{   bgp_gr(bgp) }}
{% endif %}
{% for n in bgp.neighbors %}
{%   for af in ['ipv4','ipv6'] if n[af] is defined %}
{{     ebgp_session(n,af) }}
{%   endfor %}
{% endfor %}
!
{% for af in ['ipv4','ipv6'] if af in bgp %}
{%   for n in bgp.neighbors if n[af] is defined %}
{%     if loop.first %}
 address-family {{ af }}
{%     endif %}
{{     ebgp_neighbor(n,af) }}
{%   endfor %}
{% endfor %}
```

TCP-AO is a special case: platforms differ widely in how they configure it. Arista EOS collects the secrets in global shared-secret profiles created from the **bgp._ao_secrets** list, and the neighbor references a profile by its index. Cisco IOS/IOS XR create key chains from the **bgp._ao_algo_secrets** list (see [](dev-bgp-session-node)).

(dev-bgp-session-vrf)=
## Configuring VRF BGP Instances

VRF BGP instances keep a copy of the session attributes (including **\_session_clear** and **gr**) in **vrfs._vname_.bgp**. The neighbor data is identical to the global neighbor data, and the neighbor **\_src_vrf** attribute (internal) points to the VRF. Apply the same session/address-family macros to each VRF BGP instance using the VRF **af** dictionary:

* **FRRouting** (separate `router bgp` per VRF):

  ```
  router bgp {{ bgp.as }} vrf {{ vname }}
  {% if vdata.bgp.gr is defined %}
  {{   bgp_gr(vdata.bgp) }}
  {% endif %}
  {% for af in ['ipv4','ipv6'] if af in vdata.af|default({}) %}
  {%   for n in vdata.bgp.neighbors if n[af] is defined %}
  {%     if loop.first %}
   address-family {{ af }}
  {%     endif %}
  {{     ebgp_session(n,af) }}
  {{     ebgp_neighbor(n,af) }}
  {%   endfor %}
  {% endfor %}
  ```

* **Cisco IOS** (address-family VRF context):

  ```
  {% for af in ['ipv4','ipv6'] if af in vdata.af|default({}) %}
  {%   for n in vdata.bgp.neighbors if n[af] is defined %}
  {%     if loop.first %}
   address-family {{ af }} vrf {{ vname }}
  {%     endif %}
  {{     ebgp_session(n,af) }}
  {{     ebgp_neighbor(n,af) }}
  {%   endfor %}
  {% endfor %}
  ```

(dev-bgp-session-rs)=
## BGP Route Servers

Route server support adds two attributes to the BGP neighbor data (see [](dev-bgp-session-neighbor)):

* On a **route server**, each EBGP neighbor entry carries **rs** -- the neighbor is a route server client. Configure the route server behavior (for example, `neighbor <peer> route-server-client`).
* On a **route server client**, the route server's neighbor entry carries **rs_client**, and the node-level **bgp.rs_client** attribute is set. Configure the client to accept an unexpected first AS in the AS path (for example, FRRouting and Arista EOS use `no neighbor <peer> enforce-first-as`, Cisco IOS uses a global `no bgp enforce-first-as`).

The plugin prunes the full mesh of EBGP sessions on links with route servers: only route-server-to-client sessions are retained, and **bgp.neighbors** lists are cleaned up accordingly.

(dev-bgp-session-tests)=
## Integration Tests

The integration tests for this plugin are in the `tests/integration/bgp.session/` directory:

* **01-allowas-in.yml** -- allowas-in propagation
* **02-as-override.yml** -- AS override
* **04-default-originate.yml** -- default route origination (global and VRF)
* **05-gtsm.yml** -- GTSM
* **06-passive.yml** -- passive peers
* **07-password.yml** -- MD5 passwords (global and VRF)
* **08-remove-private-as.yml** -- remove-private-as with AS-path validation
* **09-tcp-ao.yml** -- TCP-AO
* **10-timers.yml** -- keepalive/hold/min_hold timers
* **11-rs-client.yml** -- route server client behavior
* **12-rs.yml** -- route server behavior
* **13-bfd.yml** -- BFD with BGP
* **14-gr.yml** -- graceful restart states on node/VRF/neighbor level
* **24-default-unnumbered.yml** -- default route origination over unnumbered EBGP sessions

The data model details covered by this document are verified by the topology and coverage tests `tests/topology/input/bgp-rs-2as.yml` and `tests/coverage/input/bgp-default.yml`, and by the topology test `tests/topology/input/ebgp.utils.yml` (which also covers the `bgp.session.apply` parameter).