(module-services)=
# Network Services Configuration Module

The initial version of the Network Services configuration module implements [DNS clients and servers](services-dns-platform), with syslog, NTP, and SNMP planned for future releases.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(services-dns-platform)=
## DNS Support

_netlab_ can configure DNS clients or servers on these platforms:

```{features}
- title: IPv4 DNS<br>client
  enabled: |
    services.dns is True or 'ipv4' in services.dns
- title: IPv6 DNS<br>client
  enabled: |
    services.dns is True or 'ipv6' in services.dns
- title: Transport<br>VRF
  enabled: |
    services.dns and services.get('dns.transport_vrf',True) != False
- title: DNS server
  enabled: services.server.dns
```

(services-dns-parameters)=
## DNS Parameters

You can configure the DNS client with the global/node **services.dns** dictionary:

* **services.dns.domain** (string): The lab domain (default: `netlab.local`)
* **services.dns.server** (node name or list of node names): Specifies the DNS server(s) node name. The node name(s) are resolved to IPv4/IPv6 addresses, which are then used to configure the lab devices.
* **services.dns.ipv4** and **services.dns.ipv6** (address or list of addresses): Hard-coded IPv4/IPv6 DNS server addresses.
* **services.dns.transport_vrf**: the VRF used to reach the DNS server.

```{warning}
Configuring `module: [ services ]` and `services.dns.server` at the lab topology level is not enough to run DNS clients on all [host nodes](node-role-host). The hosts do not inherit topology-level modules; you have to configure the *services* module on hosts (preferably within a [group](topo-groups)).
```

The DNS server is configured with the **services.server.dns** parameter, which can be a boolean value or a dictionary with these parameters:

* **forwarder.ipv4** and **forwarder.ipv6** (address or list of addresses): upstream DNS servers used for name resolution of domains other than **services.dns.domain**.
