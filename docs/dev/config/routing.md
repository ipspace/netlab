# Generic Routing Tools Configuration Templates

This document describes the implementation details of the [](generic-routing):

* [Platform capabilities](dev-routing-platform)
* [Prefix filter data structure](dev-routing-prefix)
* [Routing policy data structure](dev-routing-policy)

Still missing:

* BGP AS-path filter data structure
* BGP community filter data structure
* Static routing data structure

(dev-routing-platform)=
## Platform Capabilities

The routing policy/filtering capabilities of individual devices are specified in the device **features.routing** dictionary. That dictionary contains a key for every component supported by the **routing** module:

* **policy** -- routing policy capabilities
* **prefix** -- prefix filters (boolean)
* **aspath** -- AS path filters (boolean)
* **community** -- BGP community filter capabilities. **expanded** key indicates that the device can use regular expressions to match BGP communities.

The **policy** capability dictionary has two elements:

* **match** -- attributes the device can use in **match** conditions (prefix, nexthop, aspath, community)
* **set** -- attributes the device can use in **set** parameters (locpref, med, weight, prepend, community)

The **match** and **set** values could be a list of supported attributes or a dictionary of attributes in case you need to specify the capabilities of individual attributes.

When using the dictionary format, set the supported attribute values to **true**; the only **set** attribute that might need more details is the **community** attribute.

**set.community** can be a dictionary with the following values:

* **standard** -- device can change **standard** communities
* **large** -- device can change **large** communities
* **extended** -- device can change **extended** communities
* **append** -- device can append communities to a BGP route

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
      match: [ prefix, nexthop, aspath, community ]
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

The *address family* complexity can be avoided on platforms that can match IPv4 and IPv6 prefixes in the same prefix filter. Here's the SR Linux template:

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

```{tip}
The routing policy entries are sorted by their sequence numbers. If your platform does not require sequence numbers in route maps, you can ignore the **‌sequence** attribute.
```

The **match** conditions in a routing policy entry include:

* **prefix** -- match the route with an IPv4 or IPv6 prefix filter
* **aspath** -- match a BGP AS-path with an AS-path filter
* **nexthop** -- match the route next hop with an IPv4 or IPv6 prefix filter
* **community** -- match BGP communities with a BGP community filter

The **set** actions include:

* **locpref** -- set local preference
* **med** -- set route metric (usually used to set BGP MED attribute)
* **weight** -- set BGP weight
* **prepend** -- do BGP AS-path prepending
* **community** -- change BGP communities attached to a route

