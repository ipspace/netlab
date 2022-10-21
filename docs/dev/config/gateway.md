# First-Hop Gateway Configuration Templates

This document describes First-Hop Gateway configuration module implementation details.

## Theory of Operation

The configuration module:

* Combines global parameters with link-level parameters
* Sets up `_reserved` list of reserved node IDs for every link
* Sets a `_stub` flag for routing modules to ignore this link
* Removes IP addresses from node interfaces if the nodes use **gateway** module, if the **gateway.protocol** is set to *anycast* and if the **gateway.anycast.unicast** is set to *False.*

Interactions with other modules:

* The interface address allocation routines avoid the reserved IDs when assigning IP addresses to individual nodes.
* Link processing code will set **gateway.ipv4** to the IP address corresponding to **gateway.id** on links with **gateway** dictionary. The **gateway** dictionary is then copied to interfaces of attached hosts to serve as the target for static routes configured on the hosts.
* Common routing protocol code removes routing protocols from links with "ignore this link" flag.

## Anycast Configuration Template Boilerplate

Use node **gateway.anycast.mac** parameter to set the shared virtual router MAC address.

When configuring anycast gateway on an interface, use the following interface parameters:

* **gateway.protocol** must be set to **anycast**.
* **gateway.ipv4** must be set to a valid IPv4 address (string)
* **gateway.anycast.mac** could be set to a link-specific shared MAC address. Ignore this parameter if your platform cannot support link-specific virtual router MAC addresses.

```
{% for l in interfaces if bfd|default(False) or l.bfd|default(False) %}
interface {{ l.ifname }}
{%   set disable_bfd = l.bfd is defined and not l.bfd %}
{%   if not disable_bfd %}
{%     set link_bfd = l.bfd|default({}) %}
 bfd interval {{ 
   link_bfd.min_tx|default(bfd.min_tx)|default(500) }} min_rx {{ 
   link_bfd.min_rx|default(bfd.min_rx)|default(500) }} multiplier {{
   link_bfd.multiplier|default(bfd.multiplier)|default(3)
   }}
!
{%   else %}
 no bfd interval
{%   endif %}
{% endfor %}
{% if bfd.min_echo_rx|default(0) %}
bfd slow-timers {{ bfd.min_echo_rx }} 
{% endif %}
```
