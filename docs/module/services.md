(module-services)=
# Network Services Configuration Module

The Network Services configuration module implements DNS and Syslog clients and servers; NTP and SNMP are planned for future releases.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

(services-platform)=
## Platform Support

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

_Syslog_ is supported on these platforms:

```{features}
- title: Syslog<br>client
  enabled: |
    services.syslog
- title: Transport<br>VRF
  enabled: |
    services.syslog and services.get('syslog.transport_vrf',True) != False
- title: Syslog server
  enabled: services.server.syslog
```

(services-common-parameters)=
## Common Network Services Parameters

You can configure the services (DNS, Syslog) clients with the global/node **services._service_** dictionary, which can contain these parameters:

* **server** (node name or list of node names): Specifies the DNS/Syslog server(s) node name. The node name(s) are resolved to IPv4/IPv6 addresses, which are then used to configure the lab devices.
* **ipv4** and **ipv6** (address or list of addresses): Hard-coded IPv4/IPv6 server addresses.
* **transport_vrf**: the VRF used to reach the DNS/Syslog server.

```{warning}
Configuring `module: [ services ]` and `services.dns.server` at the lab topology level is not enough to run DNS clients on all [host nodes](node-role-host). Hosts do not inherit topology-level modules; you must configure the *services* module on hosts (preferably within a [group](topo-groups)).
```

(services-dns-parameters)=
## DNS-Specific Parameters

* Specify the DNS server(s) on the DNS clients with the **services.dns** [common network services parameters](services-common-parameters).
* The **services.dns.domain** (string) global/node parameter sets the lab DNS domain (default: `netlab.local`)

The DNS server is enabled on supported nodes with the **services.server.dns** parameter, which can be a boolean value or a dictionary with these parameters:

* **forwarder.ipv4** and **forwarder.ipv6** (address or list of addresses): upstream DNS servers used for name resolution of domains other than **services.dns.domain**.

(services-syslog-parameters)=
## Syslog Parameters

* Specify the Syslog server(s) on client nodes with the [common network services parameters](services-common-parameters)
* The syslog server is enabled on supported nodes with the **services.server.syslog: True** parameter.
