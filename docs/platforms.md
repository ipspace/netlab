# Supported Platforms

```eval_rst
.. contents:: Table of Contents
   :depth: 1
   :local:
```

## Supported Virtual Network Devices

*netlab* supports these virtual network devices or their physical equivalents (when using *external* [virtualization provider](providers.md)). If you want to use an unsupported device in a *netlab*-managed lab, use [an unknown device](platform-unknown) or [contribute a new device implementation](dev/devices.md).

| Virtual network device                    | netlab device type |
| ----------------------------------------- | ------------------ |
| Arista vEOS                               | eos                |
| Aruba AOS-CX [❗](caveats-aruba)          | arubacx        |
| Cisco ASAv                                | asav               |
| Cisco CSR 1000v [❗](caveats-csr)         | csr                |
| Cisco IOSv [❗](caveats-iosv)             | iosv               |
| Cisco IOS XRv  [❗](caveats-iosxr)        | iosxr              |
| Cisco Nexus 9300v [❗](caveats-nxos)      | nxos               |
| Cumulus Linux 4.x/5.x [❗](caveats-cumulus) | cumulus            |
| Cumulus Linux 5.0 (NVUE) [❗](caveats-cumulus-nvue)                            | cumulus_nvue           |
| Dell OS10 [❗](caveats-os10).             | dellos10           |
| Fortinet FortiOS [❗](caveats-fortios)    | fortios            |
| FRRouting (FRR) [❗](caveats-frr)         | frr                |
| [Generic Linux host](labs/linux.md)       | linux              |
| Juniper vMX [❗](caveats-vmx)             | vmx                |
| Juniper vPTX (vJunos EVO) [❗](caveats-vptx) | vptx               |
| Juniper vSRX 3.0 [❗](caveats-vsrx)       | vsrx               |
| Mikrotik RouterOS 6 (CHR) [❗](caveats-routeros6) | routeros           |
| Mikrotik RouterOS 7 (CHR) [❗](caveats-routeros7) | routeros7           |
| Nokia SR Linux [❗](caveats-srlinux)      | srlinux            |
| Nokia SR OS [❗](caveats-sros)            | sros               |
| VyOS 1.4 [❗](caveats-vyos)               | vyos               |

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
| Aruba AOS-CX                                       |          ✅           |              ❌               |            ✅             |
| Cisco ASAv                                         |          ✅           |              ❌               |            ❌             |
| Cisco IOSv                                         |          ✅           |    ✅    |            ❌             |
| Cisco IOS XRv                                      |          ✅           |    ❌     |            ❌             |
| Cisco CSR 1000v                                    |          ✅           |    ✅    |            ❌             |
| Cisco Nexus 9300v                                  |          ✅           |              ✅               |            ❌             |
| Cumulus Linux                                      |          ✅           |              ✅               | ✅[❗](caveats-cumulus) |
| Cumulus Linux 5.0 (NVUE)                           |          ✅           |              ✅               | ✅[❗](caveats-cumulus) |
| Dell OS10                                          |          ✅           |              ❌               |            ✅             |
| Fortinet FortiOS                                   |          ✅           |              ❌               |            ❌             |
| FRR | ✅[❗](caveats-frr) | ✅[❗](caveats-frr) | ✅ |
| Generic Linux (Ubuntu/Alpine) [❗](labs/linux.md) |          ✅           |              ✅               |            ✅             |
| Juniper vMX                                        |          ❌           | ❌ |            ✅[❗](caveats-vmx)             |
| Juniper vPTX                                       |          ✅           | ❌                            |            ❌            |
| Juniper vSRX 3.0                                   |          ✅           | ✅ |            ✅[❗](caveats-vsrx)             |
| Mikrotik RouterOS 6                                |          ✅           |              ❌               |            ❌             |
| Mikrotik RouterOS 7                                |          ✅           |              ❌               |            ❌             |
| Nokia SR Linux                                     |          ❌           |              ❌               |            ✅             |
| Nokia SR OS                                        |          ❌           |              ❌               |            ✅             |
| VyOS                                               |          ✅           |              ❌               |            ✅[❗](caveats-vyos)             |

**Note:**

* *external* provider can be used with all devices supported by *netlab*.

Configuration files for Virtualbox and KVM/libvirt environments specify the number of virtual CPUs and memory allocated to individual network devices. These are the default values; you can change them with [node parameters](nodes.md#node-attributes).

| Virtual network device     | netlab device type | CPUs | memory | libvirt NIC model          |
| -------------------------- | ------------------ | ---: | -----: | -------------------------: |
| Arista vEOS                | eos                |    2 |   2048 | virtio (*libvirt default*) |
| Aruba AOS-CX               | arubacx            |    2 |   4096 | virtio (*libvirt default*) |
| Cisco ASAv                 | asav               |    1 |   2048 | virtio (*libvirt default*) |
| Cisco IOSv                 | iosv               |    1 |    512 | e1000                      |
| Cisco IOS XRv              | iosxr              |    2 |    8192 | e1000                     |
| Cisco CSR 1000v            | csr                |    2 |   4096 | virtio (*libvirt default*) |
| Cisco Nexus 9300v          | nxos               |    2 |   6144 [❗](caveats-nxos)| e1000 |
| Cumulus Linux              | cumulus            |    2 |   1024 | virtio (*libvirt default*) |
| Cumulus Linux 5.0 (NVUE)   | cumulus_nvue       |    2 |   1024 | virtio (*libvirt default*) |
| Dell OS10                  | dellos10           |    2 |   2048 | e1000                      |
| Fortinet FortiOS           | fortios            |    1 |   1024 | virtio (*libvirt default*) |
| FRR                        | frr                |    1 |   1024 | virtio (*libvirt default*) |
| Generic Linux host         | linux              |    1 |   1024 | virtio (*libvirt default*) |
| Juniper vSRX 3.0           | vsrx               |    2 |   4096 | virtio (*libvirt default*) |
| Juniper vPTX               | vptx               |    4 |   8192 | virtio (*libvirt default*) |
| Mikrotik RouterOS 6        | routeros           |    1 |    256 | virtio (*libvirt default*) |
| Mikrotik RouterOS 7        | routeros7          |    2 |    256 | e1000                      |
| VyOS                       | vyos               |    2 |   1024 | virtio (*libvirt default*) |

## Configuration Deployments

Ansible playbooks included with **netlab** can deploy and collect device configuration on these network operating systems:

| Operating system      | Deploy configuration | Collect configuration |
| --------------------- | :------------------: | :-------------------: |
| Arista EOS            |          ✅           |           ✅           |
| Aruba AOS-CX          |          ✅           |           ❌           |
| Cisco ASAv            |          ✅           |           ✅           |
| Cisco IOS / IOS XE    |          ✅           |           ✅           |
| Cisco IOS XRv         |          ✅           |           ✅           |
| Cisco Nexus OS        |          ✅           |           ✅           |
| Cumulus Linux         |          ✅           |           ✅           |
| Dell OS10             |          ✅           |           ✅           |
| Fortinet FortiOS      |          ✅           |           ✅           |
| FRR                   |  ✅[❗](caveats-frr)  | ✅[❗](caveats-frr) |
| Generic Linux         |          ✅           |           ❌           |
| Juniper vMX           |          ✅           |           ✅           |
| Juniper vSRX 3.0      |          ✅           |           ✅           |
| Juniper vPTX          |          ✅           |           ✅           |
| Mikrotik RouterOS 6   |          ✅           |           ✅           |
| Mikrotik RouterOS 7   |          ✅           |           ✅           |
| Nokia SR Linux        |          ✅           |           ✅           |
| Nokia SR OS           |          ✅           |           ✅           |
| VyOS                  |          ✅           |           ✅           |

## Initial Device Configurations

The following system-wide features are configured on supported network operating systems as part of initial device configuration:

| Operating system      | Hostname | IPv4 hosts |           LLDP            | Loopback<br />IPv4 address | Loopback<br />IPv6 address |
| --------------------- | :------: | :--------: | :-----------------------: | :------------------------: | :------------------------: |
| Arista EOS            |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Aruba AOS-CX          |    ✅     |     ❌      |             ✅             |             ✅              |             ✅              |
| Cisco ASAv            |    ✅     |     ✅      |             ❌             |             ❌              |             ❌              |
| Cisco IOS/IOS XE      |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Cisco IOS XRv         |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Cisco Nexus OS        |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Cumulus Linux         |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Cumulus Linux 5.0 (NVUE) | ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Dell OS10             |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Fortinet FortiOS      |    ✅     |     ❌      |             ✅             |             ✅              |             ✅              |
| FRR                   |    ✅     |     ✅      |             ❌             |             ✅              |             ✅              |
| Generic Linux         |    ✅     |     ✅      |  ✅[❗](linux-lldp)   |             ✅              |             ✅              |
| Juniper vMX           |    ✅     |     ❌      |             ✅             |             ✅              |             ✅              |
| Juniper vPTX          |    ✅     |     ❌      |             ✅             |             ✅              |             ✅              |
| Juniper vSRX 3.0      |    ✅     |     ❌      |             ✅             |             ✅              |             ✅              |
| Mikrotik RouterOS 6   |    ✅     |     ✅      | ✅[❗](caveats-routeros6) |             ✅              |             ✅              |
| Mikrotik RouterOS 7   |    ✅     |     ✅      | ✅[❗](caveats-routeros7) |             ✅              |             ✅              |
| Nokia SR Linux        |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Nokia SR OS           |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| VyOS                  |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |

The following interface parameters are configured on supported network operating systems as part of initial device configuration:

| Operating system      | Interface<br />description | Interface<br />bandwidth | MTU |
| --------------------- | :------------------------: | :----------------------: | :-: |
| Arista EOS            |            ✅              |            ✅            | ✅ |
| Aruba AOS-CX          |            ✅              |            ❌            | ✅ |
| Cisco ASAv            |            ✅              |            ❌            | ✅ |
| Cisco IOS/IOS XE      |            ✅              |            ✅            | ✅[❗](caveats-iosv) |
| Cisco IOS XRv         |            ✅              |            ✅ [❗](caveats-iosxr)           | ✅ |
| Cisco Nexus OS        |            ✅              |            ✅            | ✅ |
| Cumulus Linux         |            ✅              |            ✅            | ✅ |
| Cumulus Linux 5.0 (NVUE) |         ✅              |            ✅            | ❌ |
| Dell OS10             |            ✅              |            ❌            | ✅ |
| Fortinet FortiOS      |            ✅              |            ✅            | ❌ |
| FRR                   |            ✅              |            ✅            | ✅ |
| Generic Linux         |            ❌              |            ❌            | ✅ |
| Juniper vMX           |            ✅              |            ✅            | ✅ |
| Juniper vPTX          |            ✅              |            ✅            | ✅ |
| Juniper vSRX 3.0      |            ✅              |            ✅            | ✅ |
| Mikrotik RouterOS 6   |            ✅              |            ❌            | ✅ |
| Mikrotik RouterOS 7   |            ✅              |            ❌            | ✅ |
| Nokia SR Linux        |            ✅              |            ❌            | ❌ |
| Nokia SR OS           |            ✅              |            ❌            | ❌ |
| VyOS                  |            ✅              |            ❌            | ✅ |

The following interface addresses are supported on various platforms:

| Operating system      | IPv4<br />addresses | IPv6<br />addresses | Unnumbered<br />interfaces |
| --------------------- | :-----------------: | :-----------------: | :------------------------: |
| Arista EOS            |          ✅          |          ✅          |             ✅              |
| Aruba AOS-CX          |          ✅          |          ✅          |             ❌              |
| Cisco ASAv            |          ✅          |          ✅          |             ❌              |
| Cisco IOS/IOS XE      |          ✅          |          ✅          |             [❗](caveats-iosv)        |
| Cisco IOS XRv         |          ✅          |          ✅          |             ✅              |
| Cisco Nexus OS        |          ✅          |          ✅          |             ✅              |
| Cumulus Linux         |          ✅          |          ✅          |             ✅              |
| Cumulus Linux 5.0 (NVUE) |       ✅          |          ✅          |             ✅              |
| Dell OS10             |          ✅          |          ✅          |             ❌              |
| Fortinet FortiOS      |          ✅          |          ✅          |             ❌              |
| FRR                   |          ✅          |          ✅          |             ❌              |
| Generic Linux         |          ✅          |          ✅          |             ❌              |
| Juniper vMX           |          ✅          |          ✅          |             ✅              |
| Juniper vPTX          |          ✅          |          ✅          |             ✅              |
| Juniper vSRX 3.0      |          ✅          |          ✅          |             ✅              |
| Mikrotik RouterOS 6   |          ✅          |          ✅          |             ❌              |
| Mikrotik RouterOS 7   |          ✅          |          ✅          |             ❌              |
| Nokia SR Linux        |          ✅          |          ✅          |             ❌              |
| Nokia SR OS           |          ✅          |          ✅          |             ✅              |
| VyOS                  |          ✅          |          ✅          |             ✅              |

## Supported Configuration Modules

(platform-routing-support)=
Routing protocol [configuration modules](module-reference.md) are supported on these devices[^NSM]

[^NSM]: Use **[netlab show module-support](netlab/show.md)** command to display the current system settings

| Operating system      | [OSPF](module/ospf.md) | [IS-IS](module/isis.md) | [EIGRP](module/eigrp.md) | [BGP](module/bgp.md) | [BFD](module/bfd.md) | [EVPN](module/evpn.md) | [FHRP](module/gateway.md) |
| --------------------- | :--: | :---: | :---: | :-: | :-: | :--: | :--: |
| Arista EOS            | ✅   |  ✅   |   ❌   | ✅  | ✅  | ✅  | ✅  |
| Aruba AOS-CX          | ✅   |  ❌   |   ❌   | ✅  | ✅  | ✅  | ✅  |
| Cisco ASAv            | ❌   |  ✅   |  ❌   | ✅  | ❌  |  ❌  |  ❌  |
| Cisco IOSv            | ✅   |  ✅   |  ✅   | ✅  | ✅  |  ❌  | ✅  |
| Cisco IOS XE          | ✅   |  ✅   |  ✅   | ✅  | ✅  |  ❌  | ✅  |
| Cisco IOS XRv         | ✅   |  ✅   |   ❌   | ✅  |  ❌  |  ❌  |  ❌  |
| Cisco Nexus OS        | ✅   |  ✅   |  ✅   | ✅  | ✅  | ✅  | ✅  |
| Cumulus Linux         | ✅   |   ❌   |   ❌   | ✅  | ✅  | ✅  | ✅  |
| Cumulus Linux 5.0 (NVUE)        | ✅   |   ❌   |   ❌   | ✅  |  ❌  |  ❌  |  ❌  |
| Dell OS10             | [❗](caveats-os10) |   ❌   |   ❌   | ✅  | ✅  | ✅  |  ❌  |
| Fortinet FortiOS      | [❗](caveats-fortios) |   ❌   |   ❌   |   ❌   |  ❌  |  ❌  |  ❌  |
| FRR                   | ✅   |  ✅   |   ❌   | ✅  |  ❌  | ✅  |  ❌  |
| Juniper vMX           | ✅   |  ✅   |   ❌   | ✅  | ✅  |  ❌  |  ❌  |
| Juniper vPTX          | ✅   |  ✅   |   ❌   | ✅  | ✅  |  ❌  |  ❌  |
| Juniper vSRX 3.0      | ✅   |  ✅   |   ❌   | ✅  | ✅  |  ❌  |  ❌  |
| Mikrotik RouterOS 6   | ✅   |   ❌   |   ❌   | ✅  | ✅  |  ❌  |  ❌  |
| Mikrotik RouterOS 7   | ✅   |   ❌   |   ❌   | ✅  | ✅  |  ❌  |  ❌  |
| Nokia SR Linux        | ✅   |  ✅   |   ❌   | ✅  | ✅  | ✅  | ✅  |
| Nokia SR OS           | ✅   |  ✅   |   ❌   | ✅  | ✅  | ✅  | ✅  |
| VyOS                  | ✅   |  ✅   |   ❌   | ✅  | ✅  | ✅  |  ❌  |

**Notes:**
* FRHP = First-Hop Redundancy Protocol (anycast gateway or VRRP)

(platform-dataplane-support)=
The following data plane [configuration modules](module-reference.md) are supported on these devices[^NSM]:

| Operating system      | [VLAN](module/vlan.md) | [VRF](module/vrf.md) | [VXLAN](module/vxlan.md) | [MPLS](module/mpls.md) | [SR-MPLS](module/sr-mpls.md) | [SRv6](module/srv6.md) |
| --------------------- | :--: | :-: | :---: | :--: | :-----: | :--: |
| Arista EOS            |  ✅  | ✅  | ✅   | ✅   |    ✅   |  ❌   |
| Aruba AOS-CX          |  ✅  | ✅  |  ✅[❗](caveats-aruba)   | [❗](caveats-aruba)   |    ❌    |  ❌   |
| Cisco IOSv            |  ✅  | ✅  |  ❌   | ✅   |    ❌    |  ❌   |
| Cisco IOS XE          |  ✅  | ✅  | ✅   | ✅   |    ✅   |  ❌   |
| Cisco Nexus OS        |  ✅  |  ✅ | ✅   |  ❌   |    ❌    |  ❌   |
| Cumulus Linux         |  ✅  | ✅  | ✅   |  ❌   |    ❌    |  ❌   |
| Cumulus Linux 5.0 (NVUE) | ❌ |[❗](module-vrf-platform-support)|  ❌   | ❌  |   ❌    |  ❌   |
| Dell OS10             |  ✅  | ✅  |  ✅   |   ❌  |    ❌    |  ❌   |
| FRR                   |  ✅  | ✅  |  ✅   |   ✅  |    ❌   |  ❌   |
| Juniper vMX           |   ✅  |  ✅  |  ❌   |  ✅   |    ✅   |  ❌   |
| Juniper vPTX          |   ✅  |  ✅  |  ❌   |  ✅   |    ✅   |  ❌   |
| Juniper vSRX 3.0      |   ❌  |  ✅  |  ❌   |  ❌   |    ✅   |  ❌   |
| Mikrotik RouterOS 6   |  ✅  | ✅  |  ❌   | ✅   |    ❌    |  ❌   |
| Mikrotik RouterOS 7   |  ✅  | ✅  |  ❌   | ✅   |    ❌    |  ❌   |
| Nokia SR Linux        |  ✅  |  ❌  |  ❌   |  ❌   |    ✅   |  ❌   |
| Nokia SR OS           |   ❌  |  ❌  |  ❌   |  ❌   |    ✅   |  ✅  |
| VyOS                  |  ✅  | ✅  |  ✅   | ✅   |    ❌    |  ❌   |

## IPv6 Support

Core *netlab* functionality and all multi-protocol routing protocol configuration modules fully supports IPv6. OSPFv3 is implemented only on some platforms.

| Operating system      | IPv6<br />addresses | OSPFv3 | IS-IS MT | EIGRP<br />IPv6 AF | BGP<br />IPv6 AF | SR-MPLS |
| --------------------- | :-----------------: | :----: | :------: | :----------------: | :--------------: | :-----: |
| Arista EOS            |          ✅          |   ✅    |    ✅     |         ❌          |        ✅         |    ✅    |
| Aruba AOS-CX          |          ✅          |   ✅    |    ❌     |         ❌          |        ✅         |    ❌    |
| Cisco ASAv            |          ✅          |   ❌    |    ✅     |         ❌          |        ✅         |    ❌    |
| Cisco IOSv            |          ✅          |   ✅    |    ✅     |         ✅          |        ✅         |    ❌    |
| Cisco IOS XE          |          ✅          |   ✅    |    ✅     |         ✅          |        ✅         |    ❌    |
| Cisco Nexus OS        |          ✅          |   ❌    |    ✅     |         ✅          |        ✅         |    ❌    |
| Cumulus Linux         |          ✅          |   ❌    |    ✅     |         ❌          |        ✅         |    ❌    |
| Cumulus Linux 5.0 (NVUE)        |          ✅          |   ❌    |    ✅     |         ❌          |        ✅         |    ❌    |
| Dell OS10             |          ✅          |   ✅    |    ❌     |         ❌          |        ✅         |    ❌    |
| Fortinet FortiOS      |          ✅          |   ❌    |    ❌     |         ❌          |        ❌         |    ❌    |
| FRR                   |          ✅          |   ✅    |    ✅     |         ❌          |        ✅         |    ❌    |
| Generic Linux         |          ✅          |   ❌    |    ❌     |         ❌          |        ❌         |    ❌    |
| Juniper vMX           |          ✅          |   ✅    |    ✅     |         ❌          |        ✅         |    ❌    |
| Juniper vPTX          |          ✅          |   ✅    |    ✅     |         ❌          |        ✅         |    ❌    |
| Juniper vSRX 3.0      |          ✅          |   ✅    |    ✅     |         ❌          |        ✅         |    ❌    |
| Mikrotik RouterOS 6   |          ✅          |   ❌    |    ❌     |         ❌          |        ✅         |    ❌    |
| Mikrotik RouterOS 7   |          ✅          |   ✅    |    ❌     |         ❌          |        ✅         |    ❌    |
| Nokia SR Linux        |          ✅          |   ❌    |    ❌     |         ❌          |        ✅         |    ✅    |
| Nokia SR OS           |          ✅          |   ❌    |    ❌     |         ❌          |        ✅         |    ✅    |
| VyOS                  |          ✅          |   ✅    |    ✅     |         ❌          |        ✅         |    ❌    |

(platform-unknown)=
## Unknown Devices

You can use device type **unknown** to add unsupported devices to a *netlab*-managed virtual lab. *netlab* assumes an unknown device supports all configuration modules and will prepare the data structures and Ansible inventory you need to configure the device.

Unknown devices are placed in the [**unprovisioned** group](group-special-names) and are not configured by the [**netlab up**](netlab/up.md) or [**netlab initial**](netlab/initial.md) commands.

To add an unknown device to a lab:

* Set **device** node attribute to **unknown**.
* Specify Vagrant box name or container name with **image** node attribute.
* Specify **clab.kind** node attribute according to [containerlab documentation](https://containerlab.dev/manual/kinds/) when using [containerlab virtualization provider](labs/clab.md).
