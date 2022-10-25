# First-Hop Gateway Configuration Templates

This document describes First-Hop Gateway configuration module implementation details.

## Configuration Template Boilerplate

* If your device supports device-wide shared (anycast) MAC addresses, use node **gateway.anycast.mac** parameter to set the shared virtual router MAC address.

```
{% if gateway.anycast.mac is defined %}
ip virtual-router mac-address {{ gateway.anycast.mac }}
{% endif %}
```

* Iterate over interfaces and select only those that have **gateway.protocol** set
* Based on the value of **gateway.protocol** configure the desired FHRP protocol. You might want to use included files for clarity.

```
{% for intf in interfaces if intf.gateway.protocol is defined %}
interface {{ intf.ifname }}
{%   if intf.gateway.protocol == 'anycast' %}
### anycast configuration
{%   endif %}
{% endfor %}
```

## Configuring Anycast Gateways

When configuring anycast gateway on an interface, use the following interface parameters:

* **gateway.protocol** must be set to **anycast**.
* **gateway.ipv4** must be set to a valid IPv4 address (string)
* **gateway.anycast.mac** could be set to a link-specific shared MAC address. Ignore this parameter if your platform cannot support link-specific virtual router MAC addresses.

```
{% for intf in interfaces if intf.gateway.protocol is defined %}
interface {{ intf.ifname }}
{%   if intf.gateway.protocol == 'anycast' %}
  ip virtual-router address {{ intf.gateway.ipv4 }}
{%   endif %}
{% endfor %}
```
