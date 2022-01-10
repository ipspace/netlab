# Supported Platforms

The following virtual network devices are supported by *netsim-tools*:

| Virtual network device                    | netsim device type |
| ----------------------------------------- | ------------------ |
| Arista vEOS                               | eos                |
| Arrcus ArcOS                              | arcos              |
| Cisco IOSv                                | iosv               |
| Cisco CSR 1000v                           | csr                |
| Cisco Nexus 9300v                         | nxos               |
| Cumulus Linux                             | cumulus            |
| Fortinet FortiOS [❗](caveats.html#fortinet-fortios) | fortios            |
| FRR 7.5.0                                 | frr                |
| Generic Linux host                        | linux              |
| Juniper vSRX 3.0                          | vsrx               |
| Mikrotik CHR RouterOS                     | routeros           |
| Nokia SR Linux                            | srlinux            |
| Nokia SR OS [❗](caveats.html#nokia-sr-os) | sros               |
| VyOS                                      | vyos               |

**Notes:**

To specify the device type of a node in your virtual lab:

* Specify **device** property in node data

```
nodes:
- name: c_ios
  device: iosv
- name: c_csr
  device: csr
```

* Use **defaults.device** setting in lab topology

```
defaults:
  device: cumulus

nodes: [ s1, s2, s3 ]
```

See [lab topology overview](topology-overview.md) for more details.

## Supported Virtualization Providers

**netlab create** can generate configuration files for these virtualization providers:

* [vagrant-libvirt](https://github.com/vagrant-libvirt/vagrant-libvirt), including support for *veryisolated* private networks (link type: **lan**) and P2P tunnels (link type: **p2p**).
* [Vagrant VirtualBox provider](https://www.vagrantup.com/docs/providers/virtualbox)
* [Containerlab](https://containerlab.srlinux.dev/)

You cannot use all supported network devices with all virtualization providers:

| Virtual network device                             | Vagrant<br />Libvirt |   Vagrant<br />Virtualbox    |       Containerlab       |
| -------------------------------------------------- | :------------------: | :--------------------------: | :----------------------: |
| Arista vEOS                                        |          ✅           |              ✅               |            ✅             |
| Arrcus ArcOS                                       |          ✅           |              ❌               |            ❌             |
| Cisco IOSv                                         |          ✅           |    ✅    |            ❌             |
| Cisco CSR 1000v                                    |          ✅           |    ✅    |            ❌             |
| Cisco Nexus 9300v                                  |          ✅           |              ✅               |            ❌             |
| Cumulus Linux                                      |          ✅           |              ✅               | ✅[❗](caveats.html#cumulus-linux-in-containerlab) |
| Fortinet FortiOS                                   |          ✅           |              ❌               |            ❌             |
| FRR 7.5.0                                          |          ❌           |              ❌               |   ✅[❗](caveats.html#frr)   |
| Generic Linux (Ubuntu/Alpine)[❗](caveats.html#generic-linux) |          ✅           |              ✅               |            ✅             |
| Juniper vSRX 3.0                                   |          ✅           | ✅ |            ❌             |
| Mikrotik CHR RouterOS                              |          ✅           |              ❌               |            ❌             |
| Nokia SR Linux                                     |          ❌           |              ❌               |            ✅             |
| Nokia SR OS                                        |          ❌           |              ❌               |            ✅             |
| VyOS                                               |          ✅           |              ❌               |            ❌             |

## Configuration Deployments

Ansible playbooks included with **netsim-tools** can deploy and collect device configuration on these network operating systems:

| Operating system      | Deploy configuration | Collect configuration |
| --------------------- | :------------------: | :-------------------: |
| Arista EOS            |          ✅           |           ✅           |
| Arrcus ArcOS          |          ✅           |           ✅           |
| Cisco IOS / IOS XE    |          ✅           |           ✅           |
| Cisco Nexus OS        |          ✅           |           ✅           |
| Cumulus Linux         |          ✅           |           ✅           |
| Fortinet FortiOS      |          ✅           |           ✅           |
| FRR container         |          ✅           |           ❌           |
| Generic Linux         |          ✅           |           ❌           |
| Juniper vSRX 3.0      |          ✅           |           ✅           |
| Mikrotik CHR RouterOS |          ✅           |           ✅           |
| Nokia SR Linux        |          ✅           |           ❌           |
| Nokia SR OS           |          ✅           |           ❌           |
| VyOS                  |          ✅           |           ✅           |

## Initial Device Configurations

The following system-wide features are configured on supported network operating systems as part of initial device configuration:

| Operating system      | Hostname | IPv4 hosts |           LLDP            | Loopback<br />IPv4 address | Loopback<br />IPv6 address |
| --------------------- | :------: | :--------: | :-----------------------: | :------------------------: | :------------------------: |
| Arista EOS            |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Arrcus ArcOS          |    ✅     |     ❌      |             ✅             |             ✅              |             ✅              |
| Cisco IOS/IOS XE      |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Cisco Nexus OS        |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Cumulus Linux         |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Fortinet FortiOS      |    ✅     |     ❌      |             ✅             |             ✅              |             ✅              |
| FRR 7.5.0             |    ✅     |     ❌      |             ❌             |             ✅              |             ✅              |
| Generic Linux         |    ✅     |     ✅      |  ✅[❗](caveats.html#lldp)   |             ✅              |             ✅              |
| Juniper vSRX 3.0      |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Nokia SR Linux        |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Nokia SR OS           |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| VyOS                  |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Mikrotik CHR RouterOS |    ✅     |     ✅      | ✅[❗](caveats.html#mikrotik-chr-routeros) |             ✅              |             ✅              |

The following interface parameters are configured on supported network operating systems as part of initial device configuration:

| Operating system      | IPv4<br />addresses | IPv6<br />addresses | Unnumbered<br />interfaces | Interface<br />description | Interface<br />bandwidth |
| --------------------- | :-----------------: | :-----------------: | :------------------------: | :------------------------: | :----------------------: |
| Arista EOS            |          ✅          |          ✅          |             ✅              |             ✅              |            ✅             |
| Arrcus ArcOS          |          ✅          |          ✅          |             ❌              |             ❌              |            ❌             |
| Cisco IOS/IOS XE      |          ✅          |          ✅          |             ✅              |             ✅              |            ✅             |
| Cisco Nexus OS        |          ✅          |          ✅          |             ✅              |             ✅              |            ✅             |
| Cumulus Linux         |          ✅          |          ✅          |             ✅              |             ✅              |            ✅             |
| Fortinet FortiOS      |          ✅          |          ✅          |             ❌              |             ✅              |            ✅             |
| FRR 7.5.0             |          ✅          |          ✅          |             ❌              |             ✅              |            ✅             |
| Generic Linux         |          ✅          |          ✅          |             ❌              |             ❌              |            ❌             |
| Juniper vSRX 3.0      |          ✅          |          ✅          |             ✅              |             ✅              |            ✅             |
| Mikrotik CHR RouterOS |          ✅          |          ✅          |             ❌              |             ✅              |            ❌             |
| Nokia SR Linux        |          ✅          |          ✅          |             ❌              |             ✅              |            ❌            |
| Nokia SR OS           |          ✅          |          ✅          |             ❌              |             ✅              |            ❌            |
| VyOS                  |          ✅          |          ✅          |             ❌              |             ✅              |            ❌            |

## Supported Configuration Modules

Individual **netsim-tools** [configuration modules](module-reference.md) are supported on these devices:

| Operating system      | OSPF | IS-IS | EIGRP | BGP | BFD | SR-MPLS |
| --------------------- | :--: | :---: | :---: | :-: | :-: | :-----: |
| Arista EOS            | ✅   |  ✅   |   ❌   | ✅  | ✅ |    ✅   |
| Arrcus ArcOS          | ✅   |   ❌   |   ❌   |  ❌  |  ❌  |    ❌    |
| Cisco IOS             | ✅   |  ✅   |  ✅   | ✅  | ✅ |    ❌    |
| Cisco IOS XE          | ✅   |  ✅   |  ✅   | ✅  | ✅ |    ✅   |
| Cisco Nexus OS        | ✅   |  ✅   |  ✅   | ✅  | ✅ |    ❌    |
| Cumulus Linux         | ✅   |   ❌   |   ❌   | ✅  |  ❌  |    ❌    |
| Fortinet FortiOS      | [❗](caveats.html#fortinet-fortios) |   ❌   |   ❌   |   ❌   |  ❌  |    ❌    |
| FRR 7.5.0             | ✅   |  ✅   |   ❌   | ✅  |  ❌  |    ❌    |
| Generic Linux         |  ❌   |   ❌   |   ❌   |   ❌  |  ❌  |    ❌    |
| Juniper vSRX 3.0      | ✅   |  ✅   |   ❌   | ✅  | ✅  |    ❌    |
| Mikrotik CHR RouterOS | ✅   |   ❌   |   ❌   | ✅  | ✅  |    ❌    |
| Nokia SR Linux        | ✅   |  ✅   |   ❌   | ✅  | ✅  |    ✅   |
| Nokia SR OS           | ✅   |  ✅   |   ❌   | ✅  | ✅  |    ✅   |
| VyOS                  | ✅   |   ❌   |   ❌   | ✅  | ✅  |    ❌    |

## IPv6 Support

Core functionality of *netsim-tools* and all multi-protocol routing protocol configuration modules fully supports IPv6. OSPFv3 is not implemented yet.

| Operating system      | IPv6<br />addresses | OSPFv3 | IS-IS MT | EIGRP<br />IPv6 AF | BGP<br />IPv6 AF | SR-MPLS |
| --------------------- | :-----------------: | :----: | :------: | :----------------: | :--------------: | :-----: |
| Arista EOS            |          ✅          |   ❌    |    ✅     |         ❌          |        ✅         |    ✅    |
| Arrcus ArcOS          |          ✅          |   ❌    |    ❌     |         ❌          |        ❌         |    ❌    |
| Cisco IOS             |          ✅          |   ❌    |    ✅     |         ✅          |        ✅         |    ❌    |
| Cisco IOS XE          |          ✅          |   ❌    |    ✅     |         ✅          |        ✅         |    ❌    |
| Cisco Nexus OS        |          ✅          |   ❌    |    ✅     |         ✅          |        ✅         |    ❌    |
| Cumulus Linux         |          ✅          |   ❌    |    ✅     |         ❌          |        ✅         |    ❌    |
| Fortinet FortiOS      |          ✅          |   ❌    |    ❌     |         ❌          |        ❌         |    ❌    |
| FRR 7.5.0             |          ✅          |   ❌    |    ✅     |         ❌          |        ✅         |    ❌    |
| Generic Linux         |          ✅          |   ❌    |    ❌     |         ❌          |        ❌         |    ❌    |
| Juniper vSRX 3.0      |          ✅          |   ❌    |    ✅     |         ❌          |        ✅         |    ❌    |
| Mikrotik CHR RouterOS |          ✅          |   ❌    |    ❌     |         ❌          |        ✅         |    ❌    |
| Nokia SR Linux        |          ✅          |   ❌    |    ❌     |         ❌          |        ✅         |    ✅    |
| Nokia SR OS           |          ✅          |   ❌    |    ❌     |         ❌          |        ✅         |    ✅    |
| VyOS                  |          ✅          |   ❌    |    ❌     |         ❌          |        ✅         |    ❌    |
