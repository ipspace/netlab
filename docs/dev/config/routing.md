# Generic Routing Tools Configuration Templates

This document describes the implementation details of the device configuration templates (and associated platform capabilities) needed to implement [](generic-routing):

* [Platform capabilities](dev-routing-platform)
* [Prefix filter data structure](dev-routing-prefix)
* [AS-Path filter data structure](dev-routing-aspath)
* [BGP community filter data structure](dev-routing-community)
* [Static routing data structure](dev-routing-static)
* [Routing policy data structure](dev-routing-policy)

<!--
Note to reviewers: the document describes the outputs of the transformation process, not the topology elements used as its input. The outputs might differ significantly from the inputs; you have to analyze the code to determine whether the outputs are correctly described.
-->
(dev-routing-platform)=
## Platform Capabilities

The routing policy/filtering capabilities of individual devices are specified in the device **features.routing** dictionary. That dictionary contains a key for every component supported by the **routing** module:

* **policy** -- routing policy capabilities
* **prefix** -- prefix filters (boolean)
* **aspath** -- AS path filters (boolean)
* **community** -- BGP community filter capabilities. **expanded** key indicates that the device can use regular expressions to match BGP communities.

The **policy** capability dictionary has three elements:

* **match** -- attributes the device can use in **match** conditions (prefix, nexthop, aspath, community)
* **set** -- attributes the device can use in **set** parameters (locpref, med, weight, prepend, community)
* **delete** -- attributes the device can use in **delete** parameters (currently only community)

The **policy.match**, **policy.set**, and **policy.delete** values can be a list of supported attributes or a dictionary of attributes, if you need to specify the capabilities of individual attributes.

When using the dictionary format, set the supported attribute values to **true**; the only **set** attribute that might need more details is the **community** attribute.

**policy.set.community** can be a dictionary with the following values:

* **standard** -- device can change **standard** communities
* **large** -- device can change **large** communities
* **extended** -- device can change **extended** communities
* **append** -- device can append communities to a BGP route

The **policy.delete.community** attribute controls whether BGP communities can be deleted from routes. It can be:

* **true** -- device supports direct community deletion
* **false** -- device does not support community deletion
* **clist** -- device requires community lists to delete communities

It can also be a dictionary similar to the **set.community** dictionary (with the additional **list** parameter).

For example, this is the capability definition for a device that can only set MED and local preference values:

```
features:
  routing:
    policy:
      set: [ locpref, med ]
```

This is the FRRouting capability definition -- it can do almost everything supported by the routing module:

```
  routing:
    policy:
      set:
        locpref: True
        med: True
        weight: True
        prepend: True
        community:
          standard: True
          large: True
          extended: True
          append: True
      match:
        prefix: True
        nexthop: True
        aspath: True
        community:
          standard: True
          large: True
      delete:
        community: clist
    prefix: True
    aspath: True
    community:
      expanded: True
```

(dev-routing-prefix)=
## Prefix Filters Data Structure

The [](generic-routing-prefixes) are transformed into the **routing.prefix** dictionary:

* The keys are the prefix filter names
* The values are lists of prefix filter permit/deny conditions

Each entry in a prefix filter list contains these attributes:

* **action** -- `permit` or `deny`
* **sequence** -- sequence number.
* **ipv4** (optional) -- IPv4 prefix to match
* **ipv6** (optional) -- IPv6 prefix to match
* **min** (optional) -- Minimum prefix length to match. A dictionary with optional **ipv4** and **ipv6** attributes
* **max** (optional) -- Maximum prefix length to match. A dictionary with optional **ipv4** and **ipv6** attributes

```{tip}
The prefix filter entries are sorted by their sequence numbers. If your platform does not require sequence numbers in prefix filters, you can ignore the **‌sequence** attribute.
```

For example, the following prefix filters (using named prefixes and pools)...

```
routing.prefix:
  orig_1:
  - prefix: b_orig_1
  lb_only:
  - pool: loopback
    min:
      ipv4: 32
      ipv6: 64
    max:
      ipv4: 32
      ipv6: 64
```

... are transformed into the following data structure:

```
routing.prefix:
  lb_only:
  - action: permit
    ipv4: 10.0.0.0/24
    ipv6: 2001:db8:1::/48
    max:
      ipv4: 32
      ipv6: 64
    min:
      ipv4: 32
      ipv6: 64
    sequence: 10
  orig_1:
  - action: permit
    ipv4: 172.42.42.0/24
    sequence: 10
```

Many platforms cannot match IPv4 and IPv6 prefixes in the same prefix filter. _netlab_ generates an additional **routing._prefix** dictionary for those platforms, extracting the IPv4 and IPv6 components of prefix filters into separate data structures. Here's the **routing._prefix** data for the same example:

```
routing._prefix:
  ipv4:
    lb_only:
    - action: permit
      ipv4: 10.0.0.0/24
      max: 32
      min: 32
      sequence: 10
    orig_1:
    - action: permit
      ipv4: 172.42.42.0/24
      sequence: 10
  ipv6:
    lb_only:
    - action: permit
      ipv6: 2001:db8:1::/48
      max: 64
      min: 64
      sequence: 10
    orig_1:
    - action: deny
      ipv6: ::/0
      sequence: 10
```

It's straightforward to use the **routing._prefix** data to generate IPv4 and IPv6 prefix lists:

* Iterate over the address families. Use the node-level **af** attribute to iterate over address families used by a node.
* Iterate over **routing._prefix[afm]** items
* Create **prefix-list** entries.

Here's the template used to generate prefix lists for platforms using *industry-standard*[^IOL] prefix lists:

```
{%- macro min_max(p_entry) -%}
{%-  if 'min' in p_entry %} ge {{ p_entry.min }}{% endif -%}
{%-  if 'max' in p_entry %} le {{ p_entry.max }}{% endif -%}
{%- endmacro -%}
!
{% for pf_af in af if pf_af in routing._prefix|default({}) %}
{%   for p_name,p_value in routing._prefix[pf_af].items() %}
!
{%     for p_entry in p_value %}
{%.      af_kw = 'ip' if pf_af == 'ipv4' else pf_af %}
{{ af_kw }} prefix-list {{ p_name
  }}-{{ pf_af }} seq {{ p_entry.sequence }} {{ p_entry.action
  }} {{ p_entry[pf_af] }}{{ min_max(p_entry) }}
{%     endfor %}
{%   endfor %}
{% endfor %}
```

Notes:

* The template generates two prefix lists: *name*-ipv4 and *name*-ipv6. We have to use distinct names because some platforms don't like having IPv4 and IPv6 prefix lists with the same name.
* We need the **af_kw** variable because Cisco IOS CLI uses **ip prefix-list** and **ipv6 prefix-list**
* The **min_max** macro is used to make the generation of **ge**/**le** keywords a bit more readable.

[^IOL]: An euphemism for *we copied Cisco IOS CLI, but don't want to call it that way to avoid Cisco lawyers*.

The *address family* complexity can be avoided on platforms that support matching IPv4 and IPv6 prefixes in a single prefix filter (SR Linux, IOS XR). Here's the SR Linux template:

```
{% for pf_name,pf_list in routing.prefix|default({})|items %}
- path: /routing-policy/prefix-set[name={{ pf_name }}]
  value:
    prefix:
{%   for p_entry in pf_list %}{# Iterate over prefix list entries #}
{%     for p_af in af if p_af in p_entry %}{# Iterate over address families in the prefix list entry #}
    - ip-prefix: {{ p_entry[p_af] }}
{%     if p_entry.min[p_af] is defined or p_entry.max[p_af] is defined %}
      mask-length-range: {{ 
        p_entry.min[p_af]|default(p_entry[p_af]|ipaddr('prefix')) }}..{{ 
        p_entry.max[p_af]|default(32 if p_af == 'ipv4' else 128) }}
{%     else %}
      mask-length-range: exact
{%     endif %}
{%     endfor %}
{%   endfor %}
{% endfor %}
```

Notes:

* The SR Linux prefix sets don't have **sequence** or **deny** options (the lack of **deny** action is handled as a device quirk)
* SR Linux uses **ip-prefix** attribute to specify both IPv4 and IPv6 prefixes, so we have to iterate over address families to generate two list entries when a single prefix list item contains **ipv4** and **ipv6** values.
* The **mask-length-range** parameter must be in the **a..b** format, so we have to specify the default minimum and maximum lengths when they're missing.

(dev-routing-aspath)=
## AS-Path Filters Data Structure

The [](generic-routing-aspath) are transformed into the **routing.aspath** dictionary:

* The keys are the AS-path filter names
* The values are lists of AS-path filter permit/deny conditions

Each entry in an AS-path filter list contains these attributes:

* **action** -- `permit` or `deny`
* **sequence** -- sequence number.
* **path** -- AS path to match. A string containing space-separated AS numbers or AS path regular expression patterns.

```{tip}
The AS-path filter entries are sorted by their sequence numbers. If your platform does not require sequence numbers in AS-path filters, you can ignore the **sequence** attribute.
```

For example, the following AS-path filters...

```
routing.aspath:
  local_as:
  - path: 65000
  peer_as:
  - path: 65001
  transit_as:
  - path: 65000 65002
  any:
  - path: ".*"
```

... are transformed into the following data structure:

```
routing.aspath:
  local_as:
  - action: permit
    path: "65000"
    sequence: 10
  peer_as:
  - action: permit
    path: "65001"
    sequence: 10
  transit_as:
  - action: permit
    path: "65000 65002"
    sequence: 10
  any:
  - action: permit
    path: ".*"
    sequence: 10
```

Some platforms (like Cisco IOS) use numbered AS-path access lists. _netlab_ creates a **routing._numobj** dictionary that maps AS-path filter names to their numbers:

```
routing._numobj:
  aspath:
    local_as: 1
    peer_as: 2
    transit_as: 3
    any: 4
```

Here's the template used to generate AS-path access lists for FRR:

```
{% if routing.aspath|default({}) %}
{%   for asp_name,asp_list in routing.aspath.items() %}
!
{%     for asp_line in asp_list %}
bgp as-path access-list {{ asp_name }} {{ asp_line.action }} {{ asp_line.path }}
{%     endfor %}
{%   endfor %}
{% endif %}
```

(dev-routing-community)=
## BGP Community Filter Data Structure

The [](generic-routing-community) are transformed into the **routing.community** dictionary:

* The keys are the BGP community filter names
* The values are dictionaries containing the community filter definition

The community filter definition contains these attributes:

* **type** -- Community type: `standard`, `extended`, or `large`
* **cl_type** -- Filter type: `standard` or `expanded`. The `expanded` type indicates that the filter uses regular expressions.
* **regexp** -- Flag for templates: `regexp` if using regular expressions, empty string otherwise
* **value** -- List of community filter entries

Each entry in the **value** list contains these attributes:

* **action** -- `permit` or `deny`
* **sequence** -- sequence number.
* **_value** -- The community value (string). This can be a simple community (e.g., `65000:100`), a space-separated list of communities, or a regular expression pattern.
* **regexp** (optional) -- Set to the regex pattern if the value is a regular expression.

```{tip}
The community filter entries are sorted by their sequence numbers. If your platform does not require sequence numbers in community filters, you can ignore the **sequence** attribute.
```

For example, the following BGP community filters...

```
routing.community:
  customers:
    type: standard
    value:
    - action: permit
      list:
      - 65000:100
      - 65000:200
    - action: deny
      regexp: ".*"
  peers:
    type: standard
    value:
    - action: permit
      path: "65001:.*"
```

... are transformed into the following data structure:

```
routing.community:
  customers:
    type: standard
    value:
    - action: permit
      sequence: 10
      _value: 65000:100 65000:200
    - action: deny
      regexp: .*
      sequence: 20
      _value: .*
    cl_type: expanded
    regexp: regexp
  peers:
    type: standard
    value:
    - action: permit
      sequence: 10
      _value: 65001:.*
      regexp: 65001:.*
    cl_type: expanded
    regexp: regexp
```

The **type** attribute controls which CLI keyword is used to configure the community list:

* **standard** -- `community-list` (or `ip community-list` on some platforms)
* **extended** -- `extcommunity-list`
* **large** -- `large-community-list`

The **cl_type** attribute controls whether the standard or expanded form of the community list is used:

* **standard** -- Simple community list (e.g., `65000:100`)
* **expanded** -- Regular expression-based community list

Here's the template used to generate BGP community lists for FRR:

```
{% if routing.community|default({}) %}
{%   set clist_kw = { 'standard': 'community-list', 'extended': 'extcommunity-list', 'large': 'large-community-list' } %}
{%   for c_name,c_value in routing.community.items() %}
!
{%     for c_line in c_value.value %}
bgp {{ clist_kw[c_value.type] }} {{ c_value.cl_type }} {{ c_name }} {{ c_line.action }} {{ c_line._value }}
{%     endfor %}
{%   endfor %}
{% endif %}
```

(dev-routing-static)=
## Static Routing Data Structure

The [](generic-routing-static) are stored in the **routing.static** list:

* Unlike other routing objects (prefix, aspath, community), static routes are stored as a **list**, not a dictionary.
* Each entry in the list represents a single static route.

Each static route entry contains these attributes:

* **ipv4** or **ipv6** -- The prefix to route (string). Only one of these is present.
* **nexthop** -- A dictionary containing next-hop information:
  * **ipv4** or **ipv6** -- The next-hop IP address (string). Only one of these is present.
  * **intf** -- The outgoing interface name (string, for directly-connected next-hops)
  * **idx** -- The next-hop index (integer, used when multiple next-hops are available)
  * **discard** -- Set if the route goes to null/discard (used for blackhole routes)
  * **vrf** -- VRF name for inter-VRF next-hops
  * **nhlist** -- A list of next-hops (present when the next-hop was specified as a node or gateway and was expanded)
* **vrf** -- The VRF name (string, present if the static route belongs to a VRF)

For example, a simple static route...

```
routing.static:
- ipv4: 192.168.0.0/16
  nexthop:
    ipv4: 10.0.0.1
```

... is transformed into:

```
routing.static:
- ipv4: 192.168.0.0/16
  nexthop:
    ipv4: 10.0.0.1
    idx: 0
```

A static route using a node as next-hop gets expanded to include interface information:

```
routing.static:
- ipv4: 192.168.0.0/16
  nexthop:
    node: router1
```

... becomes:

```
routing.static:
- ipv4: 192.168.0.0/16
  nexthop:
    ipv4: 10.0.0.2
    intf: eth1
    idx: 0
```

### Device Features

The **routing.static** device feature dictionary can contain:

* **vrf** -- Device supports VRF static routes
* **inter_vrf** -- Device supports inter-VRF static routes (next-hop in a different VRF)
* **discard** -- Device supports discard/null routes
* **max_nexthop** -- Maximum number of next-hops per static route (default: 256)

### Template Example

Here's the template used to generate static routes for FRR:

```
{% if routing.static|default([]) %}
!
{% macro config_sr(sr_data,af) %}
{%   set cmd_af = 'ip' if af == 'ipv4' else af %}
{%   set e_vrf = ' nexthop-vrf '+(sr_data.nexthop.vrf or 'default') if 'vrf' in sr_data.nexthop else '' %}
{%   set sr_nh = 'Null0' if 'discard' in sr_data.nexthop else sr_data.nexthop[af] %}
{{ cmd_af }} route {{ sr_data[af] }} {{ sr_nh }} {{ sr_data.nexthop.intf|default('') }}{{ e_vrf }}
{% endmacro -%}
!
! Global static routes
!
{%   for sr_data in routing.static if 'vrf' not in sr_data %}
{%     for sr_af in ['ipv4','ipv6'] if sr_af in sr_data %}
{{       config_sr(sr_data,sr_af) -}}
{%     endfor %}
{%   endfor %}
{%   for r_vrf in routing.static|map(attribute='vrf',default=False)|unique if r_vrf %}
!
! VRF static routes
!
vrf {{ r_vrf }}
{%     for sr_data in routing.static if sr_data.vrf|default('') == r_vrf %}
{%       for sr_af in ['ipv4','ipv6'] if sr_af in sr_data %}
{{         config_sr(sr_data,sr_af) -}}
{%       endfor %}
{%     endfor %}
{%   endfor %}
{% endif %}
```

(dev-routing-policy)=
## Routing Policy Data Structure

The [](generic-routing-policies) are transformed into the **routing.policy** dictionary:

* The keys are the routing policy (route map) names
* The values are lists of routing policy (route map) statements (match/set values)

Each entry in a routing policy list contains these attributes:

* **action** -- `permit` or `deny`
* **sequence** -- sequence number.
* **set** -- a dictionary of **set** actions
* **match** -- a dictionary of **match** conditions
* **delete** -- a dictionary of **delete** actions (for deleting BGP communities)

```{tip}
The routing policy entries are sorted by their sequence numbers. If your platform does not require sequence numbers in route maps, you can ignore the **‌sequence** attribute.
```

The **match** conditions in a routing policy entry include:

* **prefix** -- match the route with an IPv4 or IPv6 prefix filter (string: filter name)
* **aspath** -- match a BGP AS-path with an AS-path filter (string: filter name)
* **nexthop** -- match the route next hop with an IPv4 or IPv6 prefix filter (string: filter name)
* **community** -- match BGP communities with a BGP community filter. A dictionary with **standard**, **extended**, or **large** keys, where each value is the name of a BGP community filter (string).

The **set** actions include:

* **locpref** -- set local preference (integer)
* **med** -- set route metric (usually used to set BGP MED attribute) (integer)
* **weight** -- set BGP weight (integer)
* **prepend** -- do BGP AS-path prepending. A dictionary with:
  * **count** -- number of times to prepend own AS (integer 1-32)
  * **path** -- AS number(s) to prepend (string of space-separated AS numbers)
* **community** -- change BGP communities attached to a route. A dictionary with:
  * **standard** -- list of standard BGP communities to set
  * **extended** -- list of extended BGP communities to set
  * **large** -- list of large BGP communities to set
  * **append** -- append communities instead of replacing (boolean)

The only **delete** action implemented at the moment is **delete.community**. It's a dictionary with these keys:

* **standard** -- list of standard BGP communities to delete
* **extended** -- list of extended BGP communities to delete
* **large** -- list of large BGP communities to delete
* **list** -- reference to a BGP community list to delete (a dictionary with **standard**, **extended**, or **large** keys). This key is mutually exclusive with the per-type lists; when **list** is used, no other **delete.community** attributes (**standard**, **extended**, or **large**) are present.
