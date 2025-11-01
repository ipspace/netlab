(dev-config-bgp)=
# Configuring BGP

This document describes the device data model parameters one should consider when creating a BGP device configuration template. For a wider picture, please see the [contributing new devices](../devices.md) document.

Most of the document assumes you already created an Ansible task list that is able to deploy device configuration from a template. If you plan to use Ansible modules to build initial device configuration, see [](dev-ospf-ansible-config) for more details.

**Notes:**

* The device configuration template (in Jinja2 format) should be stored in `netsim/templates/bgp/<nos>.j2` with **nos** being the value of **netlab_device_type** or **ansible_network_os** variable (see [Using Your Devices with Ansible Playbooks](../devices.md#using-your-device-with-ansible-playbooks) for more details.
* Most of the data model attributes are optional. Use `if sth is defined`, `sth|default(value)` or `if 'sth' in ifdata` in your Jinja2 templates to check for the presence of optional attributes. Try to be consistent ;)

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(dev-bgp-features)=
## Device Features

You can use the following **features.bgp** [device features](dev-device-features) to specify which BGP features your configuration template implements:

* **activate_af** -- device supports selective activation of IPv4 AF on IPv4 BGP session and IPv6 AF on IPv6 BGP session
* **community** -- Granular control of BGP community propagation see `netsim/devices/frr.yml` or `netsim/devices/eos.yml` for an example.
* **confederation** -- device supports BGP confederations
* **ipv6_lla** -- device supports unnumbered (interface) EBGP sessions
* **local_as** -- device supports **local_as** feature
* **local_as_ibgp** -- the **local_as** feature can be used to convert an EBGP session into an IBGP session
* **rfc8950** -- device supports **extended next hop** functionality that can be used to implement RFC8950-style IPv6 next hops for IPv4 AF
* **vrf_local_as** -- the **local_as** feature is supported for BGP VRF sessions
* **import** -- the list of protocols that can be redistributed into BGP. Add **vrf** to the list if the device supports redistribution into VRF BGP instances.

(dev-bgp-af)=
## Supporting Multiple Address Families

The BGP data model assumes all devices handle dual-stack deployments and provides **bgp.ipv4** and **bgp.ipv6** attributes to indicate which address families you should configure.

BGP neighbors data can contain **ipv4** and **ipv6** addresses. If a neighbor has both addresses, you have to configure two BGP neighbor sessions, one for IPv4, the other for IPv6.

_netlab_ assumes the IPv4 BGP session carries the IPv4 address family (plus other address families like MPLS/VPN or EVPN) and the IPv6 BGP session carries the IPv6 address family. It's possible to disable the default address family with the **activate** BGP neighbor attribute.

## Global BGP Parameters

*netlab* data model assumes a single BGP process running in the global routing table and VRFs. Device-wide parameters are set in **bgp** dictionary:

* **bgp.advertise_loopback** (boolean) -- When set to *True*, the BGP process should advertise the IPv4/IPv6 prefix assigned to loopback interface. You can ignore this attribute as it sets the **bgp.advertise** flag on the loopback interface
* **bgp.as** -- The BGP AS number (always present)
* **bgp.community** -- The BGP communities propagation rules -- a dictionary of neighbor types, containing a list of communities  (**standard**, **extended**, **large**) to propagate to all neighbors of that type
* **bgp.confederation.as** (optional) -- confederation-wide (external) AS
* **bgp.confederation.peers** (optional) -- list of other (internal) autonomous systems within the confederation. The local AS is not included in this list.
* **bgp.import** (optional) -- List of routing protocols (including **static** and **connected**) to be redistributed into BGP.
* **bgp.ipv4** (optional) -- You should configure IPv4 BGP address family
* **bgp.ipv6** (optional) -- You should configure IPv6 BGP address family
* **bgp.neighbors** -- A list of IBGP and EBGP neighbors
* **bgp.next_hop_self** -- When set to *True*, the BGP process should set itself as the next hop on EBGP routes propagated as IBGP routes. This attribute is propagated to the neighbor **next_hop_self** attribute and can be ignored if you configure **next-hop-self** on individual neighbors.
* **bgp.originate** (optional) -- A list of additional IPv4 prefixes that should be advertised by the BGP process. You'll probably have to create static routes to support these prefixes.
* **bgp.router_id** -- The BGP router ID
* **bgp.rr** (optional) -- When set to *True*, the device is a BGP route reflector. This attribute is propagated to the **rr_client** neighbor attribute and can be ignored if you configure **route-reflector-client** on individual neighbors.
* **bgp.rr_cluster_id** (optional) -- user-configured BGP route-reflector cluster ID. If you need a cluster ID, use `bgp.rr_cluster_id|default(bgp.router_id)`

## Interface BGP Parameters

There's a single BGP-related interface parameter:

* **bgp.advertise** (optional) -- advertise the prefix assigned to the interface in the BGP process. Used to advertise stub networks instead of doing redistribution of connected prefixes.

## BGP Neighbors

Each entry in the **bgp.neighbors** list describes an adjacent device that could be an endpoint of IBGP or EBGP sessions. A single adjacent device might have an IPv4 and an IPv6 BGP session, which would usually have to be configured as two distinct BGP neighbors.

A description of a BGP neighbor might have these parameters:

* **activate.ipv4** (optional) -- Activate the IPv4 AF on the IPv4 BGP session.
* **activate.ipv6** (optional) -- Activate the IPv6 AF on the IPv6 BGP session.
* **as** -- Remote autonomous system
* **ipv4** (optional) -- IPv4 address of an IPv4 BGP neighbor
* **ipv6** (optional) -- IPv6 address of an IPv6 BGP neighbor
* **ipv4_rfc8950** (optional) -- Activate IPv4 address family over IPv6 BGP session using RFC 8950 next hops
* **local_as** (optional) -- Local autonomous system (when using **local-as** functionality)
* **local_if** (optional) -- Local interface name for "unnumbered" BGP neighbors (EBGP sessions over IPv6 LLA configured as interface sessions)
* **name** -- Neighbor name (used in descriptions)
* **next_hop_self** (optional) -- use "next-hop-self" for this neighbor. Can contain **ebgp** (change next hop for EBGP routes) or **always** (change next hop for all routes, including reflected IBGP routes).
* **rr_client** (optional) -- the neighbor is a route-reflector client
* **replace_global_as** (optional) -- for neighbors with **local_as**, replace true AS with the local AS (typically results in **no-prepend replace-as** parameters of the **neighbor local-as** configuration command).
* **type** -- Neighbor type: **ibgp**, **ebgp**, **confed_ebgp** or **localas_ibgp**. The **confed_ebgp** type is used for intra-confederation EBGP sessions, the **localas_ibgp** type is used when the **local_as** turns an EBGP session into a fake IBGP session.
* **\_source\_intf** (optional) -- The BGP session has to originate from the specified source interface. You can use **ipv4**, **ipv6**, or **ifname** attributes of the **\_source_intf** to configure **update-source**.

## BGP Configuration Framework

The global BGP configuration should configure the BGP process and the address families. The configuration template should then use the **bgp.neighbors** list to configure individual BGP sessions, and activate those sessions within the address families. Finally, the template should originate the local prefixes. The sample code is taken from the FRRouting BGP template:

```
router bgp {{ bgp.as }}
  no bgp ebgp-requires-policy
  no bgp default ipv4-unicast
  bgp default show-hostname
  bgp default show-nexthop-hostname
{% if bgp.confederation is defined %}
  bgp confederation identifier {{ bgp.confederation.as }}
  bgp confederation peers {{ bgp.confederation.peers|join(' ') }}
{% endif %}
{% if bgp.router_id|ipv4 %}
  bgp router-id {{ bgp.router_id }}
{% endif %}
{% if bgp.rr_cluster_id|default(False) %}
  bgp cluster-id {{ bgp.rr_cluster_id }}
{% endif %}
!
{# Create neighbors #}
{# Create AFs #}
{#
    Activate neighbors, set AF attributes
#}
```

### Configure Neighbors

BGP neighbors usually have to be defined within the BGP process and then activated within address families. Iterate over IPv4/IPv6 AFs, then over BGP neighbors, and configure neighbors with matching address families:

```
{% for af in ['ipv4','ipv6'] %}
{%   for n in bgp.neighbors if n[af] is defined %}
{%     set peer = n[af] %}
  neighbor {{ peer }} remote-as {{ n.as }}
  neighbor {{ peer }} description {{ n.name }}
{%     if n._source_intf is defined %}
  neighbor {{ peer }} update-source {{ n._source_intf.ifname }}
{%     endif %}
{%     if n.local_as is defined %}
  neighbor {{ peer }} local-as {{ n.local_as }} {{ 'no-prepend replace-as' if n.replace_global_as|default(True) else '' }}
{%     endif %}
{%     if af == 'ipv6' and n.ipv4_rfc8950|default(False) %}
  neighbor {{ peer }} capability extended-nexthop
{%     endif %}
!
{%   endfor %}
{% endfor %}
```

### Configure Address Families

After configuring the BGP neighbors, you should configure individual address families defined in the **bgp** data structure. Iterate over IPv4/IPv6 and create address families as needed. Within each address family, configure:

* Route redistribution (when **bgp.import** is set)
* Prefix origination
* Address family parameters of BGP neighbors

```
{% for af in ['ipv4','ipv6'] if bgp[af] is defined %}
 address-family {{ af }} unicast
!
{# Configure redistribution #}
{# Configure prefix origination #}
{# Activate/configure neighbors #}
```

### Configure Prefix Origination

Within each address family, iterate over interfaces and create **network** statements (or whatever it takes to originate BGP prefixes) if:

* The **bgp.advertise** interface attribute is set
* The target address family is configured on the interface
* The **vrf** interface attribute matches the VRF you're configuring (or is missing for global BGP configuration)

Use **netlab_interfaces** list to include the loopback interface.

```
{%   for l in netlab_interfaces if l.bgp.advertise|default(False) and l[af] is defined and not 'vrf' in l %}
  network {{ l[af]|ipaddr(0) }}
{%   endfor %}
```

For the global IPv4 address family, check the **bgp.originate** list and advertise the prefixes listed in that list. No such mechanism exists for IPv6 prefixes or VRFs

```
{%   for pfx in bgp.originate|default([]) if af == 'ipv4' %}
  network {{ pfx|ipaddr('0') }}
{%   endfor %}
!
```

The extra prefixes configured with **bgp.originate** usually have to be supported by discard static routes. Configure those static routes outside of the BGP routing process:

```
{% for pfx in bgp.originate|default([]) %}
ip route {{ pfx|ipaddr('0') }} Null0
{% endfor %}
```

### Activate Neighbors Within Address Families

Use the neighbor **activate** attribute to figure out if a neighbor needs to be activated/configured within an address family:

```
{%   for n in bgp.neighbors if n.activate[af]|default(False) %}
{%     set peer = n[af] %}
  neighbor {{ peer }} activate
{# Configure other neighbor attributes #}
{%   endfor %}
```

Some devices configure neighbor attributes (like **next_hop_self**) within address families, others configure them per-neighbor and apply them to all address families. Whenever possible, configure neighbor attributes within the address families. Neighbor parameters configured within an address family typically include **next_hop_self** processing, route reflector clients, and BGP community propagation:

```
{%       if n.next_hop_self|default(False) %}
  neighbor {{ peer }} next-hop-self{% if n.next_hop_self == 'all' %} force{% endif +%}
{%       endif %}
{%       if n.rr_client|default(False) %}
  neighbor {{ peer }} route-reflector-client
{%       endif %}
{%       if n.type in bgp.community|default({}) %}
{%         for c_type in bgp.community[n.type] %}
  neighbor {{ peer }} send-community {{ c_type }}
{%         endfor %}
{%       endif %}
{%     endif %}
```

## Configuring RFC 8950 neighbors

If you want to support RFC 8950-type IPv4 address families, you have to be able to activate/configure the IPv4 address family on an IPv6 neighbor when the neighbor **ipv4** attribute is not a valid IPv4 address (string).

Use the following logic within the address family to figure out the neighbor IP address, then check if the **peer** is defined before trying to configure it. Use **peer** instead of **n[af]** in configuration commands.

```
{%     set peer = if n[af] is string 
                  else n.ipv6 if af == 'ipv4' and n.ipv4_rfc8950 
                  else False %}
{%     if peer %}
{%     endif %}
```

You might also have to configure **extended next hop** functionality on non-LLA IPv6 neighbors that have to support RFC 8950 next hops:

```
{% if af == 'ipv6' and n[af] is string and n.ipv4_rfc8950|default(False) %}
  neighbor {{ peer }} capability extended-nexthop
{% endif %}
```

## Configuring Unnumbered EBGP Neighbors

Unnumbered (interface) EBGP neighbors have **ipv4** and/or **ipv6** attribute set to *True* and the **local_if** attribute set to the name of the outgoing interface.

Configure BGP neighbors when **ipv4**/**ipv6** is a string, or when the **local_if** is defined. Set a variable to the peer name (AF-derived or interface-derived) to simplify the configuration template. FRRouting also requires **interface** keyword in the **neighbor** statement:

```
{% for af in ['ipv4','ipv6'] %}
{%   for n in bgp.neighbors if n[af] is defined and (n[af] is string or n.local_if is defined) %}
{%     set peer = n[af] if n[af] is string else n.local_if|default('?') %}
  neighbor {{ peer }}{{ ' interface' if peer!=n[af] else '' }} remote-as {{ n.as }}
  neighbor {{ peer }} description {{ n.name }}
...
{%   endfor %}
{% endfor %}
```

You also have to modify the "set peer name" logic in AF configuration:

```
{%   for n in bgp.neighbors if n.activate[af]|default(False) %}
{%     set peer = n[af] if n[af] is string 
                  else n.local_if if n.local_if is defined
                  else n.ipv6 if af == 'ipv4' and n.ipv4_rfc8950 
                  else False %}
{%     if peer %}
  neighbor {{ peer }} activate
...
{%     endif %}
!
{%   endfor %}
```

(dev-bgp-vrf)=
## Configuring VRF BGP Instances

VRF BGP instances contain most BGP parameters (for example, **router_id**) in the **vrfs._vname_.bgp** data structure with these exceptions:

* **ipv4** and **ipv6** parameters are not set. You should use the VRF **af** dictionary to figure out the BGP address families.
* Use the global **bgp.as** parameter to configure the BGP routing process.
* **bgp.router_id** is set only when needed/configured.
* Use VRF **networks** list instead of **bgp.advertise** interface attributes to configure prefix origination. The **networks** list contains dictionaries with **ipv4** and **ipv6** attributes. Each entry might contain one or both attributes.
* _netlab_ does not support IBGP or confederation EBGP VRF sessions. You have to be able to configure EBGP and (when implemented) local-as IBGP sessions.

At the very minimum, the VRF **bgp** data structure contains only the **neighbors** list.

Use templates similar to the ones above when configuring VRF BGP instances. The neighbor/prefix configuration is almost identical to the global BGP configuration, so it might make sense to define configuration macros to configure BGP neighbors, per-AF BGP neighbor parameters, and prefix origination. See [](dev-rip-vrf) for a very simple example, or [](dev-vrf-bgp) and [](dev-vrf-bgp-neighbor).

This is how Cisco IOS configures VRFs within the BGP routing process:

```
router bgp {{ bgp.as }}
{% for vname,vdata in vrfs.items() %}
{%   for af in ('ipv4','ipv6') if af in vdata.af|default({}) %}
 address-family {{ af }} vrf {{ vname }}
  bgp router-id {{ vdata.bgp.router_id|default(bgp.router_id) }}
{{     redistribute.config(vdata.bgp,af=af,ospf_pid=vdata.vrfidx,vrf=vname)|indent(1,first=True) }}
!
{%     for n in vdata.networks|default([]) if af in n %}
{{       bgpcfg.bgp_network(af,n[af]) }}
{%     endfor %}
!
{%     for n in vdata.bgp.neighbors|default([]) if af in n %}
{{       bgpcfg.neighbor_global(n,n[af]) }}
{{       bgpcfg.neighbor_af(n,n[af],bgp) }}
{%     endfor %}
{%   endfor %}
{% endfor %}
```
