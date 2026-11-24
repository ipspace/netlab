# First-Hop Gateway Configuration Templates

This document describes First-Hop Gateway configuration module implementation details.

## Device Features

You can use the following **features.gateway** [device features](dev-device-features) to specify which first-hop gateway features your configuration template implements:

* **protocol** -- The list of supported first-hop gateway protocols (**anycast**, **vrrp**). The **gateway** module reports an error when a node uses a protocol that is not in this list.
* **vrrp.version** -- The template implements the [**vrrp.version** plugin](plugin-vrrp-version) (configurable VRRP version). The plugin reports an error when a node using it does not have this feature.
* **caveats.anycast**, **caveats.vrrp** -- **true** or the anchor of the [caveats](platform-caveats) section describing the limitations of anycast gateways or VRRP (used only to add caveat links to the [supported features tables](dev-features-tables))

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
