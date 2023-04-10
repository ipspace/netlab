# Supported Platforms

*netlab* supports these virtual network devices or their physical equivalents (when using *external* [virtualization provider](providers.md)):

| Virtual network device                    | netlab device type |
| ----------------------------------------- | ------------------ |
| Arista vEOS                               | eos                |
| Aruba AOS-CX [❗](caveats.html#aruba-aos-cx) | arubacx        |
| Cisco ASAv                                | asav               |
| Cisco CSR 1000v                           | csr                |
| Cisco IOSv                                | iosv               |
| Cisco IOS XRv                             | iosxr [❗](caveats.html#caveats-iosxr)              |
| Cisco Nexus 9300v                         | nxos               |
| Cumulus Linux 4.x/5.x                     | cumulus            |
| Cumulus Linux 5.0 (NVUE)                            | cumulus_nvue [❗](caveats.html#caveats-cumulus-nvue)           |
| Dell OS10                                 | dellos10           |
| Fortinet FortiOS [❗](caveats.html#fortinet-fortios) | fortios            |
| FRR 7.5.0                                 | frr                |
| Generic Linux host                        | linux              |
| Juniper vMX                               | vmx                |
| Juniper vSRX 3.0                          | vsrx               |
| Mikrotik RouterOS 6 (CHR)                 | routeros           |
| Mikrotik RouterOS 7 (CHR) [❗](caveats.html#mikrotik-routeros-7) | routeros7           |
| Nokia SR Linux [❗](caveats.html#nokia-sr-linux) | srlinux            |
| Nokia SR OS [❗](caveats.html#nokia-sr-os) | sros               |
| VyOS 1.4 [❗](caveats.html#vyos)         | vyos               |

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
| Aruba AOS-CX                                       |          ✅           |              ❌               |            ❌             |
| Cisco ASAv                                         |          ✅           |              ❌               |            ❌             |
| Cisco IOSv                                         |          ✅           |    ✅    |            ❌             |
| Cisco IOS XRv                                      |          ✅           |    ❌     |            ❌             |
| Cisco CSR 1000v                                    |          ✅           |    ✅    |            ❌             |
| Cisco Nexus 9300v                                  |          ✅           |              ✅               |            ❌             |
| Cumulus Linux                                      |          ✅           |              ✅               | ✅[❗](caveats.html#cumulus-linux-in-containerlab) |
| Cumulus Linux 5.0 (NVUE)                           |          ✅           |              ✅               | ✅[❗](caveats.html#cumulus-linux-in-containerlab) |
| Dell OS10                                          |          ✅           |              ❌               |            ✅             |
| Fortinet FortiOS                                   |          ✅           |              ❌               |            ❌             |
| FRR 7.5.0                                          |          ❌           |              ❌               |   ✅[❗](caveats.html#frr)   |
| Generic Linux (Ubuntu/Alpine)[❗](caveats.html#generic-linux) |          ✅           |              ✅               |            ✅             |
| Juniper vMX                                        |          ❌           | ❌ |            ✅[❗](caveats.html#juniper-vmx-in-containerlab)             |
| Juniper vSRX 3.0                                   |          ✅           | ✅ |            ❌             |
| Mikrotik RouterOS 6                                |          ✅           |              ❌               |            ❌             |
| Mikrotik RouterOS 7                                |          ✅           |              ❌               |            ❌             |
| Nokia SR Linux                                     |          ❌           |              ❌               |            ✅             |
| Nokia SR OS                                        |          ❌           |              ❌               |            ✅             |
| VyOS                                               |          ✅           |              ❌               |            ✅[❗](caveats.html#vyos-clab)             |

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
| Cisco Nexus 9300v          | nxos               |    2 |   6144 [❗](caveats.html#cisco-nexus-os)| e1000 |
| Cumulus Linux              | cumulus            |    2 |   1024 | virtio (*libvirt default*) |
| Cumulus Linux 5.0 (NVUE)   | cumulus_nvue       |    2 |   1024 | virtio (*libvirt default*) |
| Dell OS10                  | dellos10           |    2 |   2048 | e1000                      |
| Fortinet FortiOS           | fortios            |    1 |   1024 | virtio (*libvirt default*) |
| Generic Linux host         | linux              |    1 |   1024 | virtio (*libvirt default*) |
| Juniper vSRX 3.0           | vsrx               |    2 |   4096 | virtio (*libvirt default*) |
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
| FRR container         |          ✅           |           ❌           |
| Generic Linux         |          ✅           |           ❌           |
| Juniper vMX           |          ✅           |           ✅           |
| Juniper vSRX 3.0      |          ✅           |           ✅           |
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
| FRR 7.5.0             |    ✅     |     ✅      |             ❌             |             ✅              |             ✅              |
| Generic Linux         |    ✅     |     ✅      |  ✅[❗](caveats.html#lldp)   |             ✅              |             ✅              |
| Juniper vMX           |    ✅     |     ❌      |             ✅             |             ✅              |             ✅              |
| Juniper vSRX 3.0      |    ✅     |     ❌      |             ✅             |             ✅              |             ✅              |
| Mikrotik RouterOS 6   |    ✅     |     ✅      | ✅[❗](caveats.html#mikrotik-routeros-6) |             ✅              |             ✅              |
| Mikrotik RouterOS 7   |    ✅     |     ✅      | ✅[❗](caveats.html#mikrotik-routeros-6) |             ✅              |             ✅              |
| Nokia SR Linux        |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| Nokia SR OS           |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |
| VyOS                  |    ✅     |     ✅      |             ✅             |             ✅              |             ✅              |

The following interface parameters are configured on supported network operating systems as part of initial device configuration:

| Operating system      | Interface<br />description | Interface<br />bandwidth | MTU |
| --------------------- | :------------------------: | :----------------------: | :-: |
| Arista EOS            |            ✅              |            ✅            | ✅ |
| Aruba AOS-CX          |            ✅              |            ❌            | ✅ |
| Cisco ASAv            |            ✅              |            ❌            | ✅ |
| Cisco IOS/IOS XE      |            ✅              |            ✅            | ✅[❗](caveats.html#cisco-ios) |
| Cisco IOS XRv         |            ✅              |            ✅ [❗](caveats.html#caveats-iosxr)           | ✅ |
| Cisco Nexus OS        |            ✅              |            ✅            | ✅ |
| Cumulus Linux         |            ✅              |            ✅            | ✅ |
| Cumulus Linux 5.0 (NVUE) |         ✅              |            ✅            | ❌ |
| Dell OS10             |            ✅              |            ❌            | ✅ |
| Fortinet FortiOS      |            ✅              |            ✅            | ❌ |
| FRR 7.5.0             |            ✅              |            ✅            | ✅ |
| Generic Linux         |            ❌              |            ❌            | ✅ |
| Juniper vMX           |            ✅              |            ✅            | ✅ |
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
| Cisco IOS/IOS XE      |          ✅          |          ✅          |             [❗](caveats.html#cisco-ios)        |
| Cisco IOS XRv         |          ✅          |          ✅          |             ✅              |
| Cisco Nexus OS        |          ✅          |          ✅          |             ✅              |
| Cumulus Linux         |          ✅          |          ✅          |             ✅              |
| Cumulus Linux 5.0 (NVUE) |       ✅          |          ✅          |             ✅              |
| Dell OS10             |          ✅          |          ✅          |             ❌              |
| Fortinet FortiOS      |          ✅          |          ✅          |             ❌              |
| FRR 7.5.0             |          ✅          |          ✅          |             ❌              |
| Generic Linux         |          ✅          |          ✅          |             ❌              |
| Juniper vMX           |          ✅          |          ✅          |             ✅              |
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

| Operating system      | [OSPF](module/ospf.html) | [IS-IS](module/isis.html) | [EIGRP](module/eigrp.html) | [BGP](module/bgp.html) | [BFD](module/bfd.html) | [EVPN](module/evpn.html) | [FHRP](module/gateway.html) |
| --------------------- | :--: | :---: | :---: | :-: | :-: | :--: | :--: |
| Arista EOS            | ✅   |  ✅   |   ❌   | ✅  | ✅  | ✅  | ✅  |
| Aruba AOS-CX          | ✅   |  ❌   |   ❌   | ✅  | ✅  | ✅  | ✅  |
| Cisco ASAv            | ❌   |  ✅   |  ❌   | ✅  | ❌  |  ❌  |  ❌  |
| Cisco IOSv            | ✅   |  ✅   |  ✅   | ✅  | ✅  |  ❌  | ✅  |
| Cisco IOS XE          | ✅   |  ✅   |  ✅   | ✅  | ✅  |  ❌  | ✅  |
| Cisco IOS XRv         | ✅   |  ✅   |   ❌   | ✅  |  ❌  |  ❌  |  ❌  |
| Cisco Nexus OS        | ✅   |  ✅   |  ✅   | ✅  | ✅  | ✅  | ✅  |
| Cumulus Linux         | ✅   |   ❌   |   ❌   | ✅  |  ❌  | ✅  | ✅  |
| Cumulus Linux 5.0 (NVUE)        | ✅   |   ❌   |   ❌   | ✅  |  ❌  |  ❌  |  ❌  |
| Dell OS10             | [❗](caveats.html#dell-os10) |   ❌   |   ❌   | ✅  | ✅  | ✅  |  ❌  |
| Fortinet FortiOS      | [❗](caveats.html#fortinet-fortios) |   ❌   |   ❌   |   ❌   |  ❌  |  ❌  |  ❌  |
| FRR 7.5.0             | ✅   |  ✅   |   ❌   | ✅  |  ❌  | ✅  |  ❌  |
| Juniper vMX           | ✅   |  ✅   |   ❌   | ✅  | ✅  |  ❌  |  ❌  |
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

| Operating system      | VLAN | VRF | VXLAN | MPLS | SR-MPLS | SRv6 |
| --------------------- | :--: | :-: | :---: | :--: | :-----: | :--: |
| Arista EOS            |  ✅  | ✅  | ✅   | ✅   |    ✅   |  ❌   |
| Aruba AOS-CX          |  ✅  | ✅  |  [✅](caveats.html#aruba-aos-cx)   | [❗](caveats.html#aruba-aos-cx)   |    ❌    |  ❌   |
| Cisco IOSv            |  ✅  | ✅  |  ❌   | ✅   |    ❌    |  ❌   |
| Cisco IOS XE          |  ✅  | ✅  | ✅   | ✅   |    ✅   |  ❌   |
| Cisco Nexus OS        |  ✅  |  ✅ | ✅   |  ❌   |    ❌    |  ❌   |
| Cumulus Linux         |  ✅  | ✅  | ✅   |  ❌   |    ❌    |  ❌   |
| Cumulus Linux 5.0 (NVUE) | ❌ |[❗](module/vrf.html#platform-support)|  ❌   | ❌  |   ❌    |  ❌   |
| Dell OS10             |  ✅  | ✅  |  ✅   |   ❌  |    ❌    |  ❌   |
| Juniper vMX           |   ✅  |  ✅  |  ❌   |  ✅   |    ✅   |  ❌   |
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
| FRR 7.5.0             |          ✅          |   ✅    |    ✅     |         ❌          |        ✅         |    ❌    |
| Generic Linux         |          ✅          |   ❌    |    ❌     |         ❌          |        ❌         |    ❌    |
| Juniper vMX           |          ✅          |   ✅    |    ✅     |         ❌          |        ✅         |    ❌    |
| Juniper vSRX 3.0      |          ✅          |   ✅    |    ✅     |         ❌          |        ✅         |    ❌    |
| Mikrotik RouterOS 6   |          ✅          |   ❌    |    ❌     |         ❌          |        ✅         |    ❌    |
| Mikrotik RouterOS 7   |          ✅          |   ✅    |    ❌     |         ❌          |        ✅         |    ❌    |
| Nokia SR Linux        |          ✅          |   ❌    |    ❌     |         ❌          |        ✅         |    ✅    |
| Nokia SR OS           |          ✅          |   ❌    |    ❌     |         ❌          |        ✅         |    ✅    |
| VyOS                  |          ✅          |   ✅    |    ✅     |         ❌          |        ✅         |    ❌    |
