# Supported Platforms

*netlab* supports these virtual network devices or their physical equivalents (when using *external* [virtualization provider](providers.md)):

| Virtual network device                    | netlab device type |
| ----------------------------------------- | ------------------ |
| Arista vEOS                               | eos                |
| Cisco IOSv                                | iosv               |
| Cisco CSR 1000v                           | csr                |
| Cisco Nexus 9300v                         | nxos               |
| Cumulus Linux                             | cumulus            |
| Cumulus Linux 5.0 (NVUE)                            | cumulus_nvue            |
| Fortinet FortiOS [❗](caveats.html#fortinet-fortios) | fortios            |
| FRR 7.5.0                                 | frr                |
| Generic Linux host                        | linux              |
| Juniper vSRX 3.0                          | vsrx               |
| Mikrotik CHR RouterOS                     | routeros           |
| Nokia SR Linux                            | srlinux            |
| Nokia SR OS [❗](caveats.html#nokia-sr-os) | sros               |
| VyOS 1.4 [❗](caveats.html#vyos)         | vyos               |
| Dell OS10                                 | dellos10           |

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

**netlab create** can generate configuration files for these [virtualization providers](providers.md):

* [vagrant-libvirt](https://github.com/vagrant-libvirt/vagrant-libvirt), including support for *veryisolated* private networks and UDP point-to-point tunnels.
* [Vagrant VirtualBox provider](https://www.vagrantup.com/docs/providers/virtualbox)
* [Containerlab](https://containerlab.srlinux.dev/)
* External -- *meta* virtualization provider that allows you to configure external physical or virtual devices with *netlab*

You cannot use all supported network devices with all virtualization providers. These are the supported combinations (use **[netlab show images](netlab/show.md)** command to display the current system settings).

(platform-provider-support)=

| Virtual network device | Vagrant<br />Libvirt | Vagrant<br />Virtualbox | Containerlab |
| -------------------------------------------------- | :-: | :-: | :-: |
| Arista vEOS                                        |          ✅           |              ✅               |            ✅             |
| Cisco IOSv                                         |          ✅           |    ✅    |            ❌             |
| Cisco CSR 1000v                                    |          ✅           |    ✅    |            ❌             |
| Cisco Nexus 9300v                                  |          ✅           |              ✅               |            ❌             |
| Cumulus Linux                                      |          ✅           |              ✅               | ✅[❗](caveats.html#cumulus-linux-in-containerlab) |
| Cumulus Linux 5.0 (NVUE)                           |          ✅           |              ✅               | ✅[❗](caveats.html#cumulus-linux-in-containerlab) |
| Fortinet FortiOS                                   |          ✅           |              ❌               |            ❌             |
| FRR 7.5.0                                          |          ❌           |              ❌               |   ✅[❗](caveats.html#frr)   |
| Generic Linux (Ubuntu/Alpine)[❗](caveats.html#generic-linux) |          ✅           |              ✅               |            ✅             |
| Juniper vSRX 3.0                                   |          ✅           | ✅ |            ❌             |
| Mikrotik CHR RouterOS                              |          ✅           |              ❌               |            ❌             |
| Nokia SR Linux                                     |          ❌           |              ❌               |            ✅             |
| Nokia SR OS                                        |          ❌           |              ❌               |            ✅             |
| VyOS                                               |          ✅           |              ❌               |            ❌             |
| Dell OS10                                          |          ✅           |              ❌               |            ❌             |

**Note:**

* *external* provider can be used with all devices supported by *netlab*.

Configuration files for Virtualbox and KVM/libvirt environments specify the number of virtual CPUs and memory allocated to individual network devices. These are the default values; you can change them with [node parameters](nodes.md#node-attributes).

| Virtual network device     | netlab device type | CPUs | memory | libvirt NIC model          |
| -------------------------- | ------------------ | ---: | -----: | -------------------------: |
| Arista vEOS                | eos                |    2 |   2048 | virtio (*libvirt default*) |
| Cisco IOSv                 | iosv               |    1 |    512 | e1000                      |
| Cisco CSR 1000v            | csr                |    2 |   4096 | virtio (*libvirt default*) |
| Cisco Nexus 9300v          | nxos               |    2 |   6144 [❗](caveats.html#cisco-nexus-os)| e1000 |
| Cumulus Linux              | cumulus            |    2 |   1024 | virtio (*libvirt default*) |
| Cumulus Linux 5.0 (NVUE)   | cumulus_nvue       |    2 |   1024 | virtio (*libvirt default*) |
| Fortinet FortiOS           | fortios            |    1 |   1024 | virtio (*libvirt default*) |
| Generic Linux host         | linux              |    1 |   1024 | virtio (*libvirt default*) |
| Juniper vSRX 3.0           | vsrx               |    2 |   4096 | virtio (*libvirt default*) |
| Mikrotik CHR RouterOS      | routeros           |    1 |    256 | virtio (*libvirt default*) |
| VyOS                       | vyos               |    2 |   1024 | virtio (*libvirt default*) |
| Dell OS10                  | dellos10           |    2 |   2048 | e1000                      |

## Configuration Deployments

Ansible playbooks included with **netlab** can deploy and collect device configuration on these network operating systems:

| Operating system      | Deploy configuration | Collect configuration |
| --------------------- | :------------------: | :-------------------: |
| Arista EOS            |          ✅           |           ✅           |
| Cisco IOS / IOS XE    |          ✅           |           ✅           |
| Cisco Nexus OS        |          ✅           |           ✅           |
| Cumulus Linux         |          ✅           |           ✅           |
| Fortinet FortiOS      |          ✅           |           ✅           |
| FRR container         |          ✅           |           ❌           |
| Generic Linux         |          ✅           |           ❌           |
| Juniper vSRX 3.0      |          ✅           |           ✅           |
| Mikrotik CHR RouterOS |          ✅           |           ✅           |
| Nokia SR Linux        |          ✅           |           ✅           |
| Nokia SR OS           |          ✅           |           ✅           |
| VyOS                  |          ✅           |           ✅           |
| Dell OS10             |          ✅           |           ✅           |

## Initial Device Configurations

The following system-wide features are configured on supported network operating systems as part of initial device configuration:

| Operating system      | Hostname | IPv4 hosts |           LLDP            | Loopback<br />IPv4 address | Loopback<br />IPv6 address |
| --------------------- | :------: | :--------: | :-----------------------: | :------------------------: | :------------------------: |
| Arista EOS            |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Cisco IOS/IOS XE      |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Cisco Nexus OS        |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Cumulus Linux         |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Cumulus Linux 5.0 (NVUE) | ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Fortinet FortiOS      |    ✅     |     ❌      |             ✅             |             ✅              |             ✅              |
| FRR 7.5.0             |    ✅     |     ✅      |             ❌             |             ✅              |             ✅              |
| Generic Linux         |    ✅     |     ✅      |  ✅[❗](caveats.html#lldp)   |             ✅              |             ✅              |
| Juniper vSRX 3.0      |    ✅     |     ❌      |             ✅             |             ✅              |             ✅              |
| Nokia SR Linux        |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Nokia SR OS           |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| VyOS                  |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Mikrotik CHR RouterOS |    ✅     |     ✅      | ✅[❗](caveats.html#mikrotik-chr-routeros) |             ✅              |             ✅              |
| Dell OS10             |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |

The following interface parameters are configured on supported network operating systems as part of initial device configuration:

| Operating system      | Interface<br />description | Interface<br />bandwidth | MTU |
| --------------------- | :------------------------: | :----------------------: | :-: |
| Arista EOS            |            ✅              |            ✅            | ✅ |
| Cisco IOS/IOS XE      |            ✅              |            ✅            | ✅[❗](caveats.html#cisco-ios) |
| Cisco Nexus OS        |            ✅              |            ✅            | ✅ |
| Cumulus Linux         |            ✅              |            ✅            | ✅ |
| Cumulus Linux 5.0 (NVUE) |         ✅              |            ✅            | ❌ |
| Fortinet FortiOS      |            ✅              |            ✅            | ❌ |
| FRR 7.5.0             |            ✅              |            ✅            | ✅ |
| Generic Linux         |            ❌              |            ❌            | ✅ |
| Juniper vSRX 3.0      |            ✅              |            ✅            | ✅ |
| Mikrotik CHR RouterOS |            ✅              |            ❌            | ✅ |
| Nokia SR Linux        |            ✅              |            ❌            | ❌ |
| Nokia SR OS           |            ✅              |            ❌            | ❌ |
| VyOS                  |            ✅              |            ❌            | ✅ |
| Dell OS10             |            ✅              |            ❌            | ✅ |

The following interface addresses are supported on various platforms:

| Operating system      | IPv4<br />addresses | IPv6<br />addresses | Unnumbered<br />interfaces | 
| --------------------- | :-----------------: | :-----------------: | :------------------------: | 
| Arista EOS            |          ✅          |          ✅          |             ✅              |
| Cisco IOS/IOS XE      |          ✅          |          ✅          |             [❗](caveats.html#cisco-ios)        |
| Cisco Nexus OS        |          ✅          |          ✅          |             ✅              |
| Cumulus Linux         |          ✅          |          ✅          |             ✅              |
| Cumulus Linux 5.0 (NVUE) |       ✅          |          ✅          |             ✅              |
| Fortinet FortiOS      |          ✅          |          ✅          |             ❌              |
| FRR 7.5.0             |          ✅          |          ✅          |             ❌              |
| Generic Linux         |          ✅          |          ✅          |             ❌              |
| Juniper vSRX 3.0      |          ✅          |          ✅          |             ✅              |
| Mikrotik CHR RouterOS |          ✅          |          ✅          |             ❌              |
| Nokia SR Linux        |          ✅          |          ✅          |             ❌              |
| Nokia SR OS           |          ✅          |          ✅          |             ✅              |
| VyOS                  |          ✅          |          ✅          |             ❌              |
| Dell OS10             |          ✅          |          ✅          |             ❌              |

## Supported Configuration Modules

(platform-routing-support)=
Routing protocol [configuration modules](module-reference.md) are supported on these devices (use **[netlab show module-support](netlab/show.md)** command to display the current system settings):

| Operating system      | OSPF | IS-IS | EIGRP | BGP | BFD | EVPN |
| --------------------- | :--: | :---: | :---: | :-: | :-: | :--: |
| Arista EOS            | ✅   |  ✅   |   ❌   | ✅  | ✅  | ✅  |
| Cisco IOS             | ✅   |  ✅   |  ✅   | ✅  | ✅  |  ❌  |
| Cisco IOS XE          | ✅   |  ✅   |  ✅   | ✅  | ✅  |  ❌  |
| Cisco Nexus OS        | ✅   |  ✅   |  ✅   | ✅  | ✅  |  ❌  |
| Cumulus Linux         | ✅   |   ❌   |   ❌   | ✅  |  ❌  |  ❌  |
| Cumulus Linux 5.0 (NVUE)        | ✅   |   ❌   |   ❌   | ✅  |  ❌  |  ❌  |
| Fortinet FortiOS      | [❗](caveats.html#fortinet-fortios) |   ❌   |   ❌   |   ❌   |  ❌  |  ❌  |
| FRR 7.5.0             | ✅   |  ✅   |   ❌   | ✅  |  ❌  | ✅  |
| Juniper vSRX 3.0      | ✅   |  ✅   |   ❌   | ✅  | ✅  |  ❌  |
| Mikrotik CHR RouterOS | ✅   |   ❌   |   ❌   | ✅  | ✅  |  ❌  |
| Nokia SR Linux        | ✅   |  ✅   |   ❌   | ✅  | ✅  | ✅  |
| Nokia SR OS           | ✅   |  ✅   |   ❌   | ✅  | ✅  | ✅  |
| VyOS                  | ✅   |   ✅   |   ❌   | ✅  | ✅  | ✅  |
| Dell OS10             | ✅   |   ❌   |   ❌   | ✅  | ✅  | ✅  |

(platform-module-support)=
Additional [configuration modules](module-reference.md) are supported on these devices (use **[netlab show module-support](netlab/show.md)** command to display the current system settings):

| Operating system      | VLAN | VRF | VXLAN | MPLS | SR-MPLS | SRv6 |
| --------------------- | :--: | :-: | :---: | :--: | :-----: | :--: |
| Arista EOS            |  ✅  | ✅  | ✅   | ✅   |    ✅   |  ❌   |
| Cisco IOS             |  ✅  | ✅  |  ❌   | ✅   |    ❌    |  ❌   |
| Cisco IOS XE          |   ❌  | ✅  |  ❌   | ✅   |    ✅   |  ❌   |
| Cisco Nexus OS        |  ✅  |  ✅ | ✅   |  ❌   |    ❌    |  ❌   |
| Cumulus Linux 5.0 (NVUE) | ❌ |[❗](module/vrf.html#platform-support)|  ❌   | ❌  |   ❌    |  ❌   |
| Juniper vSRX 3.0      |   ❌  |  ❌  |  ❌   |  ❌   |    ✅   |  ❌   |
| Mikrotik CHR RouterOS |  ✅  | ✅  |  ❌   | ✅   |    ❌    |  ❌   |
| Nokia SR Linux        |  ✅  |  ❌  |  ❌   |  ❌   |    ✅   |  ❌   |
| Nokia SR OS           |   ❌  |  ❌  |  ❌   |  ❌   |    ✅   |  ✅  |
| VyOS                  |  ✅  | ✅  |  ✅   | ✅   |    ❌    |  ❌   |
| Dell OS10             |  ✅  | ✅  |  ✅   |   ❌  |    ❌    |  ❌   |

## IPv6 Support

Core *netlab* functionality and all multi-protocol routing protocol configuration modules fully supports IPv6. OSPFv3 is implemented only on some platforms.

| Operating system      | IPv6<br />addresses | OSPFv3 | IS-IS MT | EIGRP<br />IPv6 AF | BGP<br />IPv6 AF | SR-MPLS |
| --------------------- | :-----------------: | :----: | :------: | :----------------: | :--------------: | :-----: |
| Arista EOS            |          ✅          |   ✅    |    ✅     |         ❌          |        ✅         |    ✅    |
| Cisco IOS             |          ✅          |   ✅    |    ✅     |         ✅          |        ✅         |    ❌    |
| Cisco IOS XE          |          ✅          |   ✅    |    ✅     |         ✅          |        ✅         |    ❌    |
| Cisco Nexus OS        |          ✅          |   ❌    |    ✅     |         ✅          |        ✅         |    ❌    |
| Cumulus Linux         |          ✅          |   ❌    |    ✅     |         ❌          |        ✅         |    ❌    |
| Cumulus Linux 5.0 (NVUE)        |          ✅          |   ❌    |    ✅     |         ❌          |        ✅         |    ❌    |
| Fortinet FortiOS      |          ✅          |   ❌    |    ❌     |         ❌          |        ❌         |    ❌    |
| FRR 7.5.0             |          ✅          |   ✅    |    ✅     |         ❌          |        ✅         |    ❌    |
| Generic Linux         |          ✅          |   ❌    |    ❌     |         ❌          |        ❌         |    ❌    |
| Juniper vSRX 3.0      |          ✅          |   ❌    |    ✅     |         ❌          |        ✅         |    ❌    |
| Mikrotik CHR RouterOS |          ✅          |   ❌    |    ❌     |         ❌          |        ✅         |    ❌    |
| Nokia SR Linux        |          ✅          |   ❌    |    ❌     |         ❌          |        ✅         |    ✅    |
| Nokia SR OS           |          ✅          |   ❌    |    ❌     |         ❌          |        ✅         |    ✅    |
| VyOS                  |          ✅          |   ✅    |    ✅     |         ❌          |        ✅         |    ❌    |
| Dell OS10             |          ✅          |   ✅    |    ❌     |         ❌          |        ✅         |    ❌    |
