(supported-platforms)=
# Supported Platforms

```eval_rst
.. contents:: Table of Contents
   :depth: 1
   :local:
```

(platform-devices)=
## Supported Virtual Network Devices

*netlab* supports these virtual network devices or their physical equivalents (when using *external* [virtualization provider](providers.md)).

| Virtual network device | netlab device type | support level |
| -----------------------| ------------------ | ------------- |
| Arista vEOS/cEOS [❗](caveats-eos) | eos    | full          |
| Aruba AOS-CX [❗](caveats-aruba) | arubacx  | full          |
| Cisco 8000v [❗](caveats-cisco8000v) | cisco8000v | minimal |
| Cisco ASAv [❗](caveats-asav)    | asav     | minimal       |
| Cisco Catalyst 8000v [❗](caveats-cat8000v) | cat8000v | full |
| Cisco CSR 1000v [❗](caveats-csr) | csr     | full          |
| Cisco IOS-on-Linux (IOL) [❗](caveats-iol) | iol | full     |
| Cisco IOS-on-Linux L2 image (IOL L2)[❗](caveats-iol) | ioll2               | full |
| Cisco IOSv [❗](caveats-iosv)      | iosv   | full          |
| [Cisco IOSvL2](https://developer.cisco.com/docs/modeling-labs/iosvl2/#iosvl2) [❗](caveats-iosv)   | iosvl2 | full |
| Cisco IOS XRv  [❗](caveats-iosxr) | iosxr  | minimal       |
| Cisco Nexus 9300v [❗](caveats-nxos) | nxos | best effort   |
| Cumulus Linux 4.x/5.x [❗](caveats-cumulus) | cumulus | end of life |
| Cumulus Linux 5.x (NVUE) [❗](caveats-cumulus-nvue) | cumulus_nvue | minimal |
| Dell OS10 [❗](caveats-os10) | dellos10     | full          | 
| Fortinet FortiOS [❗](caveats-fortios) | fortios | minimal  |
| FRRouting (FRR) [❗](caveats-frr) | frr     | full          |
| [Generic Linux host](labs/linux.md) | linux | full          |
| Juniper vMX [❗](caveats-vmx) | vmx         | best effort   |
| Juniper vPTX (vJunos EVO) [❗](caveats-vptx) | vptx | full  |              
| Juniper vSRX 3.0 [❗](caveats-vsrx) | vsrx  | best effort   |
| vJunos-switch [❗](caveats-vjunos-switch) | vjunos-switch | full |
| vJunos-router [❗](caveats-vjunos-router) | vjunos-router | full |
| Mikrotik RouterOS 6 (CHR) [❗](caveats-routeros6) | routeros           | end of life |
| Mikrotik RouterOS 7 (CHR) [❗](caveats-routeros7) | routeros7           | minimal |
| Nokia SR Linux [❗](caveats-srlinux) | srlinux | full       |
| Nokia SR OS [❗](caveats-sros)    | sros    | best effort[^SROSBE]   |
| Nokia SR-SIM [❗](caveats-srsim)  | srsim   | full          |
| OpenBSD [❗](caveats-openbsd)     | openbsd | best effort   |
| Sonic [❗](caveats-sonic)         | sonic   | minimal       |
| VyOS 1.4 [❗](caveats-vyos)       | vyos    | full          |

[^SROSBE]: With the launch of the Nokia SR SIM, we stopped running integration tests for the SR-OS VM, assuming the behavior of the two products would be nearly identical.

(platform-daemons)=
*netlab* also supports the following daemons (control-plane software running in containers):

| Daemon          | netlab device type | support level |
| --------------- | ------------------ | ------------- |
| BIRD Internet Routing Daemon [❗](caveats-bird) | bird               | full |
| dnsmasq DHCP server [❗](caveats-dnsmasq) | dnsmasq | full |

You can also run network management software and even some network services products (for example, NetScaler) as [custom Linux containers](tutorial-linux-custom).

The support level of a platform is defined as:

* **full** -- a core contributor is regularly implementing new features. We run a [full suite of integration tests](https://release.netlab.tools/) for every release that could impact the device behavior (for example, due to changes in configuration templates).
* **best effort** -- while a core contributor might still work on the platform, we don't run integration tests (usually due to limited availability of the VM/container image). YMMV.
* **minimal** -- don't expect too much[^WTLTB]. What you see is pretty much what you'll get (and in many cases, it did not go through integration tests).
* **end-of-life** -- these platforms are still part of _netlab_ package because the storage prices keep falling.

[^WTLTB]: Particularly on platforms that take way too long to boot, like Cisco IOS XR. We're all forced to deal with a limited lifespan.

```{tip}
Use **netlab show devices** to display the up-to-date device list and device support levels.
```

(platform-host)=
Most devices behave as routers (or layer-3 switches); the following devices can take multiple roles or behave as [IP hosts](node-router-host):

| Device | router | host | bridge |
|-----------------------|:--:|:--:| :--:|
| Arista EOS            | ✅ | ✅ | ✅ |
| Bird                  | ✅ | ✅ | ❌  |
| Cisco IOS/IOS XE[^18v]| ✅ | ✅ | ✅ |
| dnsmasq               | ❌  | ✅ | ❌  |
| FRRouting             | ✅ | ✅ | ❌  |
| Generic Linux         | ❌  | ✅ | ✅ |
| Open BSD              | ✅ | ✅ | ❌  |

**Notes:**

* Use the **[netlab show devices](netlab-show-devices)** command to display the list of supported devices and daemons.
* You can specify the device type in the **device** property of the [node data](node-attributes) or the topology-wide **[defaults.device](default-device-type)** setting. See [lab topology overview](topology-overview.md) for more details.
* If you want to use an unsupported device in a *netlab*-managed lab, use [an unknown device](platform-unknown) or [contribute a new device implementation](dev/devices.md).
* The daemons run on top of Ubuntu Linux and use the same scripts as Linux for initial device configuration. See *linux* device for initial configuration capabilities.

## Supported Virtualization Providers

**netlab create** can generate configuration files for these [virtualization providers](providers.md):

* [vagrant-libvirt](https://github.com/vagrant-libvirt/vagrant-libvirt), including support for *veryisolated* private networks and UDP point-to-point tunnels.
* [Vagrant VirtualBox provider](https://www.vagrantup.com/docs/providers/virtualbox)
* [Containerlab](https://containerlab.srlinux.dev/)
* External -- *meta* virtualization provider that allows you to configure external physical or virtual devices with *netlab*

You cannot use all supported network devices with all virtualization providers. These are the supported combinations (use **[netlab show images](netlab/show.md)** command to display the current system settings).

(platform-provider-support)=

| Virtual network device | Vagrant<br />[Libvirt](labs/libvirt.md) | Vagrant<br />[Virtualbox](labs/virtualbox.md) | [Containerlab](labs/clab.md) |
| ------------------ | :-: | :-: | :-: |
| Arista vEOS        | [✅](build-eos)  | ✅  | [✅](build-ceos)  |
| Aruba AOS-CX       | [✅](build-arubacx)  |  ❌  |  ✅[❗](clab-vrnetlab)  |
| Cisco 8000v        |  ❌  |  ❌  | ✅ |
| Cisco ASAv         | [✅](build-asav)  |  ❌  |  ❌  |
| Cisco Catalyst 8000v | [✅](build-cat8000v) |  ❌  |  ✅[❗](clab-vrnetlab)  |
| Cisco CSR 1000v    | [✅](build-csr)  | ✅  |  ✅[❗](clab-vrnetlab) |
| Cisco IOL          |  ❌ | ❌  |  ✅[❗](clab-vrnetlab) |
| Cisco IOL L2       |  ❌ | ❌  |  ✅[❗](clab-vrnetlab) |
| Cisco IOSv         | [✅](build-iosv)  | ✅  |  ✅[❗](clab-vrnetlab) |
| Cisco IOSvL2       | [✅](build-iosvl2)|  ❌  | ✅[❗](clab-vrnetlab) |
| Cisco IOS XRv      | [✅](build-iosxr) |  ❌  | ✅  |
| Cisco Nexus 9300v  | [✅](build-nxos) | ✅  |  ✅[❗](clab-vrnetlab)  |
| Cumulus Linux      | ✅  | ✅  | ✅[❗](caveats-cumulus) |
| Cumulus Linux 5.x (NVUE) | ✅ | ✅ | ✅[❗](caveats-cumulus) |
| Dell OS10          | [✅](build-dellos10)  |  ❌  | ✅  |
| Fortinet FortiOS   | ✅  |  ❌  |  ✅  |
| FRR | ✅[❗](caveats-frr) | ✅[❗](caveats-frr) | ✅ |
| Generic Linux (Ubuntu/Alpine) [❗](labs/linux.md) | ✅  | ✅  | ✅  |
| Juniper vMX        |  ❌  |  ❌  | ✅[❗](clab-vrnetlab)   |
| Juniper vPTX       | [✅](build-vptx)  |  ❌  | ✅[❗](clab-vrnetlab)  |
| Juniper vSRX 3.0   | [✅](build-vsrx)  | ✅  | ✅[❗](caveats-vsrx)  |
| vJunos-switch       |  ❌  |  ❌  | ✅[❗](clab-vrnetlab) |
| vJunos-router       |  ❌  |  ❌  | ✅[❗](clab-vrnetlab) | | Mikrotik RouterOS 6 | ✅  |  ❌  |  ❌  |
| Mikrotik RouterOS 7 | [✅](build-chr7)  |  ❌  |  ❌  |
| Nokia SR Linux      |  ❌  |  ❌  | ✅  |
| Nokia SR OS         |  ❌  |  ❌  | ✅  |
| Nokia SR-SIM        |  ❌  |  ❌  | ✅  |
| OpenBSD             | [✅](build-openbsd)  |  ❌  | [✅](clab-vrnetlab) |
| Sonic               | [✅](build-sonic)  |  ❌  |  ❌  | 
| VyOS                | ✅  |  ❌  | ✅[❗](caveats-vyos) |

**Note:**

* *external* provider can be used with all devices supported by *netlab*.

Configuration files for Virtualbox and KVM/libvirt environments specify the number of virtual CPUs and memory allocated to individual network devices. These are the default values; you can change them with [node parameters](nodes.md#node-attributes).

| Virtual network device     | netlab<br>device type | CPUs | memory | libvirt NIC model          |
| -------------------------- | ------------------ | ---: | -----: | -------------------------: |
| Arista vEOS                | eos                |    2 |   2048 | virtio |
| Aruba AOS-CX               | arubacx            |    2 |   4096 | virtio |
| Cisco ASAv                 | asav               |    1 |   2048 | virtio |
| Cisco Catalyst 8000v       | cat8000v           |    2 |   4096 | virtio |
| Cisco CSR 1000v            | csr                |    2 |   4096 | virtio |
| Cisco IOSv                 | iosv               |    1 |    512 | e1000                      |
| Cisco IOSvL2               | iosvl2             |    1 |    1024 | e1000                      |
| Cisco IOS XRv              | iosxr              |    2 |    8192 | e1000                     |
| Cisco Nexus 9300v          | nxos               |    2 |   6144 [❗](caveats-nxos)| e1000 |
| Cumulus Linux              | cumulus            |    2 |   1024 | virtio |
| Cumulus Linux 5.x (NVUE)   | cumulus_nvue       |    2 |   1024 | virtio |
| Dell OS10                  | dellos10           |    2 |   2048 | e1000                      |
| Fortinet FortiOS           | fortios            |    1 |   2048 | virtio |
| FRR                        | frr                |    1 |   1024 | virtio |
| Generic Linux host         | linux              |    1 |   1024 | virtio |
| Juniper vSRX 3.0           | vsrx               |    2 |   4096 | virtio |
| Juniper vPTX               | vptx               |    4 |   8192 | virtio |
| Mikrotik RouterOS 6        | routeros           |    1 |    256 | virtio |
| Mikrotik RouterOS 7        | routeros7          |    2 |    256 | e1000                      |
| OpenBSD                    | openbsd            |    1 | 1024 | virtio |
| Sonic                      | sonic              |    2 | 4096 | virtio |
| VyOS                       | vyos               |    2 |   1024 | virtio |

```{tip}
**‌virtio** is the default KVM/libvirt NIC model.
```

## Configuration Deployments

Ansible playbooks included with **netlab** can deploy and collect device configuration on these network operating systems:

(platform-config-support)=
| Operating system      | Deploy<br>configuration | Collect<br> configuration | Configurable<br>save to startup |
| --------------------- |:--:|:--:|:--:|
| Arista EOS            | ✅ | ✅ |
| Aruba AOS-CX          | ✅ | ✅ |
| Cisco ASAv            | ✅ | ✅ |
| Cisco IOS/IOS XE[^18v]| ✅ | ✅ |
| Cisco IOS XR[^XR]     | ✅ | ✅ |
| Cisco Nexus OS        | ✅ | ✅ |
| Cumulus Linux         | ✅ | ✅ |
| Dell OS10             | ✅ | ✅ | ✅ |
| Fortinet FortiOS      | ✅ | ❌  |
| FRR                   |  ✅[❗](caveats-frr)  | ✅[❗](caveats-frr) |
| Generic Linux         | ✅ | ❌  |
| Junos[^Junos]         | ✅ | ✅ |
| Mikrotik RouterOS 6   | ✅ | ✅ |
| Mikrotik RouterOS 7   | ✅ | ✅ |
| Nokia SR Linux        | ✅ | ✅ |
| Nokia SR OS[^SROS]    | ✅ | ✅ |
| OpenBSD               | ✅ | ❌  |
| Sonic                 | ✅ | ✅ |
| VyOS                  | ✅ | ✅ |

[^18v]: Includes Cisco CSR 1000v, Cisco Catalyst 8000v, Cisco IOS-on-Linux (IOL) and IOL Layer-2 image

[^Junos]: Includes vMX, vSRX, vPTX, vJunos-switch, and vJunos-router

[^SROS]: Includes the Nokia SR-SIM container and the Virtualized 7750 SR and 7950 XRS Simulator (vSIM) virtual machine

[^XR]: Includes IOS XRv, IOS XRd, and Cisco 8000v

## Initial Device Configurations

The following system-wide features are configured on supported network operating systems as part of the initial device configuration:

(platform-initial-config)=
| Operating system      | Hostname | IPv4/IPv6<br>hosts |           LLDP            | IPv4<br>Loopback | IPv6<br>Loopback |
| --------------------- | :------: | :--------: | :-----------------------: | :------------------------: | :------------------------: |
| Arista EOS               | ✅  | ✅  | ✅  | ✅  | ✅  |
| Aruba AOS-CX             | ✅  |  ❌  | ✅  | ✅  | ✅  |
| Cisco ASAv               | ✅  | ✅  |  ❌  |  ❌  |  ❌  |
| Cisco IOS/IOS XE[^18v]   | ✅  | ✅  | ✅  | ✅  | ✅  |
| Cisco IOS XR[^XR]        | ✅  | ✅  | ✅  | ✅  | ✅  |
| Cisco Nexus OS           | ✅  | ✅  | ✅  | ✅  | ✅  |
| Cumulus Linux            | ✅  | ✅[^HIF]  | ✅  | ✅  | ✅  |
| Cumulus Linux 5.x (NVUE) | ✅  | ✅  | ✅  | ✅  | ✅  |
| Dell OS10                | ✅  | ✅  | ✅  | ✅  | ✅  |
| Fortinet FortiOS         | ✅  |  ❌  | ✅  | ✅  | ✅  |
| FRR                      | ✅  | ✅[^HIF]  |  ❌  | ✅  | ✅  |
| Generic Linux            | ✅  | ✅[^HIF]  |  ✅[❗](linux-lldp) | ✅  | ✅  |
| Junos[^Junos]            | ✅  |  ❌  | ✅  | ✅  | ✅  | 
| Mikrotik RouterOS 6      | ✅  | ✅  | ✅[❗](caveats-routeros6) | ✅ | ✅ |
| Mikrotik RouterOS 7      | ✅ | ✅ | ✅[❗](caveats-routeros7) | ✅ | ✅ |
| Nokia SR Linux           | ✅  | ✅  | ✅  | ✅  | ✅  |
| Nokia SR OS[^SROS]       | ✅  | ✅  | ✅  | ✅  | ✅  |
| OpenBSD                  | ✅  | ✅  |  ❌  | ✅  | ✅  |
| Sonic                    | ✅  | ✅  |  ❌  | ✅  | ✅  |
| VyOS                     | ✅  | ✅  | ✅  | ✅  | ✅  |

[^HIF]: Some Linux-based devices can also use interface names in host names. See [/etc/hosts file on Linux](linux-hosts) for more details.

(platform-initial-interfaces)=
The following interface parameters are configured on supported network operating systems as part of the initial device configuration:

| Operating system      | Interface<br />description | Interface<br />bandwidth | MTU | Additional<br />loopbacks
| --------------------- |:---:|:---:|:---:|:---:|
| Arista EOS            | ✅  | ✅  | ✅  | ✅  |
| Aruba AOS-CX          | ✅  |  ❌  | ✅  | ✅  |
| Cisco ASAv            | ✅  |  ❌  | ✅  |  ❌  |
| Cisco IOS/IOS XE[^18v]| ✅  | ✅  | ✅[❗](caveats-iosv) | ✅  |
| Cisco IOS XR[^XR]     | ✅  | ✅ [❗](caveats-iosxr) | ✅ | ✅ |
| Cisco Nexus OS        | ✅  | ✅  | ✅  | ✅  |
| Cumulus Linux         | ✅  | ✅  | ✅  | ✅  |
| Cumulus Linux 5.x (NVUE) | ✅ | ❌ | ✅  | ✅  |
| Dell OS10             | ✅  |  ❌  | ✅  | ✅  |
| Fortinet FortiOS      | ✅  | ✅  |  ✅[❗](caveats-fortios)  |  ❌  |
| FRR                   | ✅  | ✅  | ✅  | ✅  |
| Generic Linux         |  ❌  |  ❌  | ✅  |  ❌  |
| Junos[^Junos]         | ✅  | ✅  | ✅  |  ❌  |
| Mikrotik RouterOS 6   | ✅  |  ❌  | ✅  |  ❌  |
| Mikrotik RouterOS 7   | ✅  |  ❌  | ✅  | ✅  |
| Nokia SR Linux        | ✅  |  ❌  | ✅  | ✅  |
| Nokia SR OS[^SROS]    | ✅  |  ❌  | ✅  | ✅  |
| OpenBSD               |  ❌  |  ❌  | ✅  |  ❌  |
| Sonic                 | ✅  | ✅  | ✅  | ✅  |
| VyOS                  | ✅  |  ❌  | ✅  | ✅  |

(platform-initial-addresses)=
The following interface addresses are supported on various platforms:

| Operating system      | IPv4<br />addresses | IPv6<br />addresses | Unnumbered<br />IPv4 interfaces | Configurable<br>IPv6 RA |
| --------------------- | :-: | :-: | :-: | :-: |
| Arista EOS            | ✅  | ✅  | ✅  | ✅  |
| Aruba AOS-CX          | ✅  | ✅  | ✅  |  ❌  |
| Cisco ASAv            | ✅  | ✅  |  ❌  |  ❌  |
| Cisco IOSv/IOSvL2     | ✅  | ✅  |  ❌  | ✅  |
| Cisco IOS XE[^18v]    | ✅  | ✅  | ✅  | ✅  |
| Cisco IOS XR[^XR]     | ✅  | ✅  | ✅  |  ❌  |
| Cisco Nexus OS        | ✅  | ✅  | ✅  |  ❌  |
| Cumulus Linux         | ✅  | ✅  | ✅  |  ❌  |
| Cumulus Linux 5.x (NVUE) | ✅ | ✅ | ✅ |  ❌  |
| Dell OS10             | ✅  | ✅  |  ❌  |  ❌  |
| Fortinet FortiOS      | ✅  | ✅  |  ❌  |  ❌  |
| FRR                   | ✅  | ✅  | ✅  | ✅  |
| Generic Linux         | ✅  | ✅  |  ❌  |  ❌  |
| Junos[^Junos]         | ✅  | ✅  | ✅  |  ❌  |
| Mikrotik RouterOS 6   | ✅  | ✅  |  ❌  |  ❌  |
| Mikrotik RouterOS 7   | ✅  | ✅  |  ❌  |  ❌  |
| Nokia SR Linux        | ✅  | ✅  |  ❌  |  ❌  |
| Nokia SR OS[^SROS]    | ✅  | ✅  | ✅  |  ❌  |
| OpenBSD               | ✅  | ✅  |  ❌  |  ❌  |
| Sonic                 | ✅  | ✅  | ✅  |  ❌  |
| VyOS                  | ✅  | ✅  | ✅  |  ❌  |

```{tip}
* Use **‌netlab show modules -m initial** to display optional initial configuration features supported by individual devices
* See [Initial Configuration Integration Tests Results](https://release.netlab.tools/_html/coverage.initial) for up-to-date details.
```

(platform-initial-extra)=
Some platforms can enable additional functionality during the initial device configuration:

| Operating system | [Debugging<br>attribute](node-debug-attribute)[^GNDA] |
|------------------|:-:|
| Cisco IOS/IOS XE[^18v]| **ios.debug** |
| FRRouting             | **frr.debug** |

[^GNDA]: The debugging attribute can be specified for a single node or globally, in which case the debugging is activated on all nodes using the specified device.

## Supported Configuration Modules

(platform-routing-support)=
Routing protocol [configuration modules](module-reference.md) are supported on these devices[^NSM]

[^NSM]: Use **[netlab show module-support](netlab/show.md)** command to display the current system settings

| Operating system      | [OSPF](module/ospf.md) | [IS-IS](module/isis.md) | [EIGRP](module/eigrp.md) | [BGP](module/bgp.md) | [RIPv2/ng](module/ripv2.md)
| --------------------- | :--: | :--: | :--: | :--: | :--: |
| Arista EOS            | ✅   |  ✅  |   ❌  |  ✅  |  ✅  |
| Aruba AOS-CX          | ✅   |  ❌   |   ❌  |  ✅  |   ❌  |
| Cisco ASAv            | ❌    |  ✅  |   ❌  |  ✅  |   ❌  |
| Cisco IOSv/IOSvL2     | ✅   |  ✅  |  ✅  |  ✅  |  ✅  |
| Cisco IOS XE[^18v]    | ✅   |  ✅  |  ✅  |  ✅  |  ✅  |
| Cisco IOS XR[^XR]     | ✅   |  ✅  |   ❌  |  ✅  |   ❌  |
| Cisco Nexus OS        | ✅   |  ✅  |  ✅  |  ✅  |   ❌  |
| Cumulus Linux         | ✅   |   ❌  |   ❌  |  ✅  |  ✅  |
| Cumulus Linux 5.x (NVUE) | ✅ |  ❌  |   ❌   | ✅ [❗](caveats-cumulus-nvue)  |  ❌  |
| Dell OS10             | ✅ [❗](caveats-os10) |   ❌   |   ❌   | ✅  |  ❌  |
| Fortinet FortiOS      | ✅ [❗](caveats-fortios) |   ❌   |   ❌   |   ❌   |  ❌  |
| FRR                   | ✅   |  ✅   |   ❌  | ✅  |  ✅  |
| Junos[^Junos]         | ✅   |  ✅   |   ❌  | ✅  |   ❌  |
| Mikrotik RouterOS 6   | ✅   |   ❌   |   ❌  | ✅  |   ❌  |
| Mikrotik RouterOS 7   | ✅   |   ❌   |   ❌  | ✅  |   ❌  |
| Nokia SR Linux        | ✅   |  ✅   |   ❌  | ✅  |   ❌  |
| Nokia SR OS[^SROS]    | ✅   |  ✅   |   ❌  | ✅  | ✅  |
| OpenBSD               | ✅   |   ❌   |   ❌  |  ❌  | ✅   |
| Sonic                 |  ❌   |   ❌   |   ❌  | ✅  |   ❌  |
| VyOS                  | ✅   |  ✅   |   ❌  | ✅  |   ❌  |

Routing protocol [configuration modules](module-reference.md) are also supported on these daemons:

| Operating system      | [OSPF](module/ospf.md) | [IS-IS](module/isis.md) | [BGP](module/bgp.md) | [RIPv2/ng](module/ripv2.md) |
|------------------------------|:--:|:--:|:--:|:--:|
| BIRD Internet Routing Daemon | ✅ [❗](caveats-bird) | ❌ | ✅ [❗](caveats-bird) | ❌ |

These devices support additional control-plane protocols or BGP address families:

| Operating system | [BFD](module/bfd.md) | [EVPN](module/evpn.md) | [MPLS/VPN](module/mpls.md) | [FHRP](module/gateway.md) |
| --------------------- | :-: | :-: | :-: | :-: |
| Arista EOS            | ✅  | ✅  | ✅  | ✅  |
| Aruba AOS-CX          | ✅  | ✅  | ✅  | ✅  |
| Cisco CSR 1000v       | ✅  |  ❌  | ✅  | ✅  |
| Cisco Catalyst 8000v  | ✅  |  ❌  |  ❌  | ✅  |
| Cisco IOSv/IOSvL2     | ✅  |  ❌  | ✅  | ✅  |
| Cisco Nexus OS        | ✅  | ✅  |  ❌  | ✅  |
| Cumulus Linux         | ✅  | ✅  |  ❌  | ✅  |
| Dell OS10             | ✅  | ✅  |  ❌  |  ❌  |
| FRR                   | ✅  | ✅  | ✅  |  ❌  |
| Juniper vMX           | ✅  |  ❌  | ✅  | ✅  |
| Juniper vPTX          | ✅  |  ❌  | ✅  | ✅  |
| Juniper vSRX 3.0      | ✅  |  ❌  |  ❌  | ✅  |
| vJunos-switch         | ✅  |  ✅ |  ❌  | ✅  |
| vJunos-router         | ✅  |  ❌  |  ❌  | ✅  |
| Mikrotik RouterOS 6   | ✅  |  ❌  | ✅  |  ❌  |
| Mikrotik RouterOS 7   | ✅  |  ❌  | ✅  |  ❌  |
| Nokia SR Linux        | ✅  | ✅  |  ❌  | ✅  |
| Nokia SR OS[^SROS]    | ✅  | ✅  | ✅  | ✅  |
| VyOS                  | ✅  | ✅  | ✅  |  ❌  |

**Notes:**
* FRHP = First-Hop Redundancy Protocol (anycast gateway or VRRP)

(platform-layer-2-support)=
The layer-2 control plane [configuration modules](module-reference.md) are supported on these devices[^NSM]:

| Operating system          | [Spanning<br>Tree Protocol](module/stp.md) | [Link Aggregation<br>Groups](module/lag.md) |
| ------------------------- |:--:|:--:|
| Arista EOS                | ✅ | ✅ |
| Aruba CX                  | ✅ | ✅ |
| bird                      | ❌  | ✅ |
| Cumulus Linux             | ✅ | ✅ |
| Cumulus Linux 5.x (NVUE)  | ✅ | ✅ |
| Dell OS10                 | ✅ | ✅ |
| dnsmasq                   | ❌  | ✅ |
| FRR                       | ✅ | ✅ |
| Linux                     | ❌  | ✅ |

(platform-dataplane-support)=
The data plane [configuration modules](module-reference.md) are supported on these devices[^NSM]:

| Operating system      | [VLAN](module/vlan.md) | [VRF](module/vrf.md) | [VXLAN](module/vxlan.md) | [MPLS](module/mpls.md) | [SR-MPLS](module/sr-mpls.md) | [SRv6](module/srv6.md) |
| --------------------- |:--:|:--:|:--:|:--:|:--:|:--:|
| Arista EOS            | ✅ | ✅ | ✅ | ✅ | ✅ |  ❌ |
| Aruba AOS-CX          | ✅ | ✅ |  ✅[❗](caveats-aruba) | [❗](caveats-aruba) | ❌ | ❌ |
| Cisco 8000v (IOS/XR)  | ✅ | ✅ |  ❌ |  ❌ |  ❌ |  ❌ |
| Cisco Catalyst 8000v  | ✅ | ✅ |  ❌ | ✅ | ✅ | ✅ |
| Cisco CSR 1000v       | ✅ | ✅ | ✅ | ✅ | ✅ |  ❌ |
| Cisco IOL (IOS/XE)    | ✅ | ✅ |  ❌ | ✅ | ✅ | ✅ |
| Cisco IOSv/IOSvL2     | ✅ | ✅ |  ❌ | ✅ |  ❌ |  ❌ |
| Cisco Nexus OS        | ✅ | ✅ | ✅ |  ❌ |  ❌ |  ❌ | 
| Cumulus Linux         | ✅ | ✅ | ✅ |  ❌ |  ❌ |  ❌ |
| Cumulus Linux 5.x (NVUE) | ✅ |[❗](module-vrf-platform-support)| ❌ | ❌ | ❌ | ❌ |
| Dell OS10             | ✅ | ✅ | ✅ |  ❌ |  ❌ |  ❌ | 
| FRR                   | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Juniper vMX           | ✅ | ✅ |  ❌ | ✅ | ✅ |  ❌ | 
| Juniper vPTX          | ✅ | ✅ |  ❌ | ✅ | ✅ |  ❌ | 
| Juniper vSRX 3.0      | ❌  | ✅ |  ❌ |  ❌ |  ❌ |  ❌ |
| vJunos-switch         | ✅ | ✅ | ✅ |  ❌ |  ❌ |  ❌ |
| vJunos-router         | ❌  | ✅ |  ❌ |  ❌ |  ❌ |  ❌ |
| Mikrotik RouterOS 6   | ✅ | ✅ |  ❌ | ✅ |  ❌ |  ❌ |
| Mikrotik RouterOS 7   | ✅ | ✅ |  ❌ | ✅ |  ❌ |  ❌ |
| Nokia SR Linux        | ✅ | ✅ | ✅ |  ❌ | ✅ |  ❌ |
| Nokia SR OS[^SROS]    | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| VyOS                  | ✅ | ✅ | ✅ | ✅ |  ❌ |  ❌ |

(platform-services-support)=
Network services [configuration modules](module-reference.md) are supported on these devices[^NSM]

| Operating system      | [DHCP](module/dhcp.md) | [DHCPv6](module/dhcp.md) |
| --------------------- | :--: | :--: |
| Arista EOS            | ✅   |  ✅  |
| Cisco CSR 1000v       | ✅   |  ✅  |
| Cisco IOSv/IOSvL2     | ✅   |  ✅  |
| Cumulus Linux         | ✅   |  ✅  |

Network services [configuration modules](module-reference.md) are also supported on these daemons:

| Operating system      | [DHCP](module/dhcp.md) | [DHCPv6](module/dhcp.md) |
| --------------------- | :--: | :--: |
| dnsmasq               | ✅   |  ✅  |

```{tip}
See [integration test results](https://release.netlab.tools/) for more details.
```

## IPv6 Support

Core *netlab* functionality and all multi-protocol routing protocol configuration modules fully support IPv6. However, you might not be able to configure IPv6 versions of some routing protocols on all platforms.

| Operating system      | OSPFv3 | IS-IS MT | EIGRP<br />IPv6 AF | BGP<br />IPv6 AF | SR-MPLS |
| --------------------- |:--:|:--:|:--:|:--:|:--:|
| Arista EOS            | ✅ | ✅ | ❌ | ✅ | ✅ |
| Aruba AOS-CX          | ✅ | ❌ | ❌ | ✅ | ❌ |
| Cisco ASAv            | ❌ | ✅ | ❌ | ✅ | ❌ |
| Cisco IOSv/IOSvL2     | ✅ | ✅ | ✅ | ✅ | ❌ |
| Cisco IOS XE[^18v]    | ✅ | ✅ | ✅ | ✅ | ❌ |
| Cisco IOS XR[^XR]     | ✅ | ✅ | ❌ | ✅ | ❌ |
| Cisco Nexus OS        | ✅ | ✅ | ✅ | ✅ | ❌ |
| Cumulus Linux 4.x     | ✅ | ❌ | ❌ | ✅ | ❌ |
| Cumulus Linux NVUE    |  ❌ | ❌ | ❌ | ✅ | ❌ |
| Dell OS10             | ✅ | ❌ | ❌ | ✅ | ❌ |
| FRR                   | ✅ | ✅ | ❌ | ✅ | ❌ |
| Junos[^Junos]         | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| Mikrotik RouterOS 6   |  ❌ | ❌ | ❌ | ✅ | ❌ |
| Mikrotik RouterOS 7   | ✅ | ❌ | ❌ | ✅ | ❌ |
| Nokia SR Linux        | ✅ | ✅ | ❌ | ✅ | ✅ |
| Nokia SR OS[^SROS]    | ✅ | ✅ | ❌ | ✅ | ✅ |
| Sonic                 |  ❌ | ❌ | ❌ | ✅ | ❌ |
| VyOS                  | ✅ | ✅ | ❌ | ✅ | ❌ |

(platform-unknown)=
## Unknown Devices

You can use device type **unknown** to add unsupported devices to a *netlab*-managed virtual lab. *netlab* assumes an unknown device supports all configuration modules and will prepare the data structures and Ansible inventory you need to configure the device.

Unknown devices are placed in the [**unprovisioned** group](group-special-names) and are not configured by the [**netlab up**](netlab/up.md) or [**netlab initial**](netlab/initial.md) commands.

To add an unknown device to a lab:

* Set **device** node attribute to **unknown**.
* Specify Vagrant box name or container name with **image** node attribute.
* Specify **clab.kind** node attribute according to [containerlab documentation](https://containerlab.dev/manual/kinds/) when using [containerlab virtualization provider](labs/clab.md).
