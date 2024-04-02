# Platform Caveats

```eval_rst
.. contents:: Table of Contents
   :depth: 1
   :local:
   :backlinks: none
```

(caveats-eos)=
## Arista EOS

* Routed VLANs cannot be used in EVPN MPLS VLAN bundles
* Arista EOS uses an [invalid value for the suboption 150 of the DHCP option 82](https://blog.ipspace.net/2023/03/netlab-vrf-dhcp-relay.html#vendor-interoperability-is-fun) when doing inter-VRF DHCPv4 relaying.
* The DHCP client on Arista EOS is finicky. Management interface might lose its IPv4 address when the DHCP state changes on one of the data-plane Ethernet interfaces.

The following features do not work on Arista cEOS Ethernet interfaces:

* MPLS encapsulation
* Anycast gateways
* DHCP and DHCPv6 clients

(caveats-aruba)=
## Aruba AOS-CX

* Ansible automation of Aruba AOS-CX requires the installation of the [ArubaNetworks Ansible Collection](https://galaxy.ansible.com/arubanetworks/aoscx) with `ansible-galaxy collection install arubanetworks.aoscx`.
* Limitations of the Aruba AOS-CX Simulator can be found [here](https://feature-navigator.arubanetworks.com/), selecting *CX Simulator* as platform.

### VRF and L3VPN Caveats

* OSPF processes can be only *1-63*. VRF indexes usually are > 100, so a device tweak will map every *vrfidx* to a different OSPF process id. That means you cannot have more than 62 VRF using OSPF.
* On the Aruba AOS-CX Virtual version *10.11.0001*, MPLS L3VPN forwarding plane seems broken (while the control plane is working fine).

### VXLAN and EVPN Caveats

* The VXLAN dataplane (at least, on the virtual version) seems not supporting VNI greater than 65535. If you set an higher value, an overflow will occur, and you may have overlapping VNIs. The workaround for this is to set, i.e., `defaults.vxlan.start_vni: 20000` and `defaults.evpn.start_transit_vni: 10000` (especially on multi-vendor topologies).
* EVPN Symmetric IRB is supported only from the Aruba AOS-CX Virtual version *10.13*. Additionally:
  * CPU generated traffic does not get encapsulated in Symmetric IRB on AOS-CX Simulator.
  * Active-Gateway MAC Addresses shall be the same across all VTEPs in AOS-CX Simulator.

(caveats-bird)=
## BIRD Internet Routing Daemon

* You have to build the BIRD container image with the **netlab clab build bird** command.
* BIRD is implemented as a pure control-plane daemon running on a Linux VM or as a container with a single external interface. You can set the node **role** to **router** to turn a BIRD instance into a more traditional networking device with a loopback interface.
* _netlab_ installs BIRD software in a container image or a VM on top of Ubuntu 22.04. The current version of BIRD shipping with Ubuntu 22.04 is 2.0.8.
* BIRD supports a single router ID that is used for BGP and OSPF.
* The VM or container running BIRD starts with static routes pointing to one of the adjacent routers (see [host routes on Linux](linux-routes)). BGP and OSPF routes learned by BIRD are copied into the kernel IP routing table.

### OSPF Caveats

* BIRD OSPF implementation has no *reference bandwidth*. The default OSPF cost is 10.

### BGP Caveats

* You must run OSPF on the BIRD daemon for the IBGP sessions to work.
* BIRD will not advertise (reflect) an IBGP route if it has an equivalent OSPF route.
* You cannot configure BGP community propagation on BIRD. All BGP communities are always propagated to all neighbors.

### IPv6 Caveats

* OSPFv3 does not advertise the prefix configured on the loopback interface even when the loopback interface is part of the OSPFv3 process.
* If the BGP next hop of a reflected IBGP route is reachable as an OSPF route, BIRD advertises a link-local address as one of the next hops of the IBGP IPv6 prefix, potentially resulting in broken IPv6 connectivity.

(caveats-csr)=
## Cisco CSR 1000v

* Cisco CSR 1000v does not support interface MTU lower than 1500 bytes or IP MTU higher than 1500 bytes.
* VLAN subinterfaces can be configured on Cisco CSR 1000v but do not work. CSR 1000v cannot be used as a router-on-a-VLAN-trunk device.

See also Cisco IOSv OSPF and BGP caveats.

(caveats-iosv)=
## Cisco IOSv

* Cisco IOSv release 15.x does not support unnumbered interfaces. Use Cisco CSR 1000v.
* BGP configuration is optimized to result in reasonable convergence times under lab conditions. Do not use the same settings in a production network.
* Multiple OSPFv2 processes on Cisco IOS cannot have the same OSPF router ID. By default, _netlab_ generates the same router ID for global and VRF OSPF processes, resulting in non-fatal configuration errors that Ansible silently ignores.
* The OSPFv3 process on Cisco IOS advertises loopback addresses as /128 prefixes unless the OSPF network type is set to `point-to-point`. _netlab_ configures OSPFv3 `point-to-point` network type on all loopback interfaces to get results comparable to other implementations.

(caveats-iosxr)=
## Cisco IOS XRv

* netlab was tested with IOS XR release 7.4. Earlier releases might use a different management interface name, in which case you'll have to set **defaults.devices.iosxr.mgmt_if** parameter to the name of the management interface
* Copying Vagrant public insecure SSH key into IOS XR during the box building process is cumbersome. The vagrant configuration file uses a fixed SSH password.
* Maximum interface bandwidth on IOS XRv is 1 Gbps (1000000).
* It seems IOS XR starts an SSH server before it parses the device configuration[^WCPGW], and newer versions of Vagrant don't like that and will ask you for the password for user **vagrant**. Ignore that prompt and the subsequent error messages[^POT], and you might get a running lab in a few minutes[^MAS].
* The IOS XRd container seems to be a resource hog. If you experience errors during the initial device configuration, reduce the number of parallel configuration processes -- set the ANSIBLE_FORKS environment variable to one with `export ANSIBLE_FORKS=1`.

[^WCPGW]: Yeah, what could possibly go wrong?

[^POT]: You'll get plenty of those. Even when the IOS XR device is configured and you can log into the console, it hates accepting SSH sessions.

[^MAS]: Hint: you have plenty of time to make coffee and a snack.

(caveats-nxos)=
## Cisco Nexus OS

* Nexus OS release 9.3 runs in 6 GB of RAM (*netlab* system default).
* Nexus OS release 10.1 requires 8 GB of RAM and will fail with a cryptic message claiming it's running on unsupported hardware when it doesn't have enough memory.
* Nexus OS release 10.2 requires at least 10 GB of RAM and crashes when you try to run it as an 8 GB VM.
* To change the default amount of memory used by a **nxos** device, set the **defaults.devices.nxos.memory** parameter (in MB)[^DD]

[^DD]: See [](topology/hierarchy.md) for an in-depth explanation of why attributes with hierarchical names work in *netlab*

(caveats-cumulus)=
## Cumulus Linux

* The Cumulus VX 4.4.0 Vagrant box for VirtualBox is broken. *netlab* is using Cumulus VX 4.3.0 with *virtualbox* virtualization provider.

_netlab_ uses the VLAN-aware bridge paradigm to configure VLANs on Cumulus Linux. That decision results in the following restrictions:

* *ifupdown2* version shipping with Cumulus Linux 4.4.0 refuses to create VLAN subinterfaces in combination with a VLAN-aware bridge. The _netlab_-generated Cumulus Linux VLAN configuration, therefore, cannot use routed subinterfaces.
* *ifupdown2* enslaves physical ports to the bridge, and subsequently cannot configure IP addresses on physical ports. The _netlab_-generated Cumulus Linux VLAN configuration, therefore, cannot use routed native VLAN.

### Running Cumulus Linux in Containerlab

* *containerlab* could run Cumulus Linux as a [container or as a micro-VM with *firecracker*](https://containerlab.dev/manual/kinds/cvx/). The default used by *netlab* is to run Cumulus Linux as a container. To change that, add **clab.runtime** parameter to node data.
* Cumulus Linux ran as a container might report errors related to DHCP client during initial configuration, in which case you might have to disable **apparmor** for DHCP client to get it to run. The hammer-of-Thor command to fix this problem is `sudo systemctl disable apparmor` followed by a reboot, your sysadmin friends probably have a better suggestion.
* *netlab* uses Cumulus VX containers created by Michael Kashin and downloaded from his Docker Hub account. Once Nvidia releases an official container image, change the container name with **defaults.devices.cumulus.clab.image**[^DD] parameter (or by editing the `topology-defaults.yml` file included with *netlab*).

(caveats-cumulus-nvue)=
## Cumulus 5.0 with NVUE

You could configure Cumulus Linux 5.0 with configuration templates developed for Cumulus Linux 4.0 (use device type **cumulus** and specify desired device image), or with NVUE.

NVUE has several shortcomings that prevent *netlab* from configuring basic designs like IBGP on top of IGP. Don't be surprised if the labs that work with **cumulus** device don't work with **cumulus_nvue** device, and please create a GitHub issue whenever you find a glitch. We'd love to know (at least) what doesn't work as expected.

To run Cumulus Linux 5.x with **cumulus** device type, add the following lines to your lab topology[^DD]:

```
defaults.devices.cumulus.libvirt.image: CumulusCommunity/cumulus-vx:5.2.0
defaults.devices.cumulus.libvirt.memory: 2048
```

Alternatively, you could add the following lines to your `~/.topology-defaults.yml` file:

```
devices.cumulus.libvirt.image: CumulusCommunity/cumulus-vx:5.2.0
devices.cumulus.libvirt.memory: 2048
```

(caveats-os10)=
## Dell OS10

Dell OS10 uses a concept of a so-called *Virtual Network* interface to try to handle transparently VLANs and VXLANs in the same way. However, it seems that right now it is **NOT** possible to activate OSPF on a *Virtual Network* (VLAN) SVI interface.

Sadly, it's also **NOT** possible to use *VRRP* on a *Virtual Network* interface (but *anycast* gateway is supported). At the same time, *anycast* gateway is not supported on plain *ethernet* interfaces, so you need to use *VRRP* there.

(caveats-dnsmasq)=
## dnsmasq DHCP server

* You have to build the *dnsmasq* container image with the **netlab clab build dnsmasq** command.

(caveats-fortios)=
## Fortinet FortiOS

* *FortiOS* VM images by default have a 15 day evaluation license. The VM has [limited capabilities](https://docs.fortinet.com/document/fortigate-private-cloud/6.0.0/fortigate-vm-on-kvm/504166/fortigate-vm-virtual-appliance-evaluation-license) without a license file. It will work for 15 days from first boot, at which point you must install a license file or recreate the vagrant box completely from scratch.
* Ansible automation of FortiOS requires the installation of the [FortiOS Ansible Collection 2.1.3 or greater](https://galaxy.ansible.com/fortinet/fortios) and a FortiOS version > 6.0.

### OSPF Caveats

* Fortinet implementation of OSPF configuration module does not implement per-interface OSPF areas. All interfaces belong to the OSPF area defined in the node data.
* Fortinet configuration templates set OSPF network type based on number of neighbors, not based on **ospf.network_type** link/interface parameter.

(caveats-frr)=
## FRR

* Many FRR configuration templates are not idempotent -- you cannot run **netlab initial** multiple times. Non-idempotent templates include VLAN and VRF configurations.
* VM version of FRR is a Ubuntu VM. FRR package is downloaded and installed during the initial configuration process.
* You can change FRR default profile with **netlab_frr_defaults** node parameter (`traditional` or `datacenter`, default is `datacenter`).
* **netlab collect** downloads FRR configuration but not Linux interface configuration.
* FRR container needs host kernel modules for MPLS forwarding. If your Ubuntu 22.04 distribution does not include the MPLS drivers, do `sudo apt install linux-generic`.

(caveats-vmx)=
## Juniper vMX in Containerlab

Juniper vMX runs as a container in _containerlab_. You have to use _vrnetlab_ to build the container from a vMX disk image. See [_containerlab_ documentation](https://containerlab.dev/manual/kinds/vr-vmx/) for further details.

The Juniper vMX image in *vrnetlab* uses the network `10.0.0.0/24` for its own internal network, which conflicts with the default network used by **netlab** for the loopback addressing. See [](clab-vrnetlab) for details.

(caveats-vptx)=
## Juniper vPTX

* *netlab* release 1.7.0 supports only vJunosEvolved releases that do not require external PFE- and RPIO links. The first vJunosEvolved release implementing internal PFE- and RPIO links is the release 23.2R1-S1.8.

The rest of this section lists information you might find helpful if you're a long-time Junos user:

* vJunos Evolved (vJunos EVO, Juniper vPTX) uses Linux instead of BSD as the underlying OS. There are some basic differences from a "default" JunOS instance, including the management interface name, which is `re0:mgmt-0`.
* After the VM boots up, you need to wait for the *virtual FPC* to become *Online* before being able to forward packets. You can verify this with `show chassis fpc`. **NOTE**: You can see the network interfaces only after the *FPC* is online.
* It seems that the DHCP Client of the management interface does not install a default route, even if received by the DHCP server.
* The VM will complain about missing licenses. You can ignore that.

(caveats-vsrx)=
## Juniper vSRX in Containerlab

You can run Juniper vSRX as a container packaged by *vrnetlab*. See [_containerlab_ documentation](https://containerlab.dev/manual/kinds/vr-vsrx/) for further details.

The Juniper vSRX image in *vrnetlab* uses the network `10.0.0.0/24` for its own internal network, which conflicts with the default network used by **netlab** for the loopback addressing. See [](clab-vrnetlab) for details.

vSRX container built with *vrnetlab* uses **flow based forwarding**. You have two ways to use it:

* Configure security zones, and attach interfaces and rules to them;
* Change the mode to [**packet based forwarding**](https://supportportal.juniper.net/s/article/SRX-How-to-change-forwarding-mode-for-IPv4-from-flow-based-to-packet-based).

(caveats-routeros6)=
## Mikrotik RouterOS 6

* Runs with the *CHR* image.
* LLDP on Mikrotik CHR RouterOS is enabled on all the interfaces.
* The CHR free license offers full features with a 1Mbps upload limit per interface, upgradeable to an unrestricted 60-day trial by registering a free MikroTik account and using the ```/system license renew``` command.

(caveats-routeros7)=
## Mikrotik RouterOS 7

* Runs with the *CHR* image.
* LLDP on Mikrotik CHR RouterOS is enabled on all the interfaces.
* The CHR free license offers full features with a 1Mbps upload limit per interface, upgradeable to an unrestricted 60-day trial by registering a free MikroTik account and using the ```/system license renew``` command.
* At the time of the build, testing is being performed with releases **7.5** (claimed as *stable*) and **7.6beta8**. On both of them:
  * MPLS dataplane seems to have issues when using *virtio* networking, while the LDP and VPNv4 control plane work fine. With *e1000* everything works fine.
  * BGP-based route leaking is working on the control plane, but not on the dataplane.

(caveats-srlinux)=
## Nokia SR Linux
* Only supported on top of *Containerlab*
* Supports container image release 23.3.1 or later (due to YANG model changes)
* Requires the latest Ansible Galaxy collection 'nokia.grpc' and its dependencies to be installed from the git repo. You can also use the **netlab install grpc** command to install them
* MPLS and LDP only supported on 7250 IXR (clab.type in ['ixr6','ixr6e','ixr10','ixr10e'])

```
ansible-galaxy collection install git+https://github.com/nokia/ansible-networking-collections.git#/grpc/
python3 -m pip install grpcio protobuf==3.20.1
```

* As of September 2023, the Nokia Ansible Galaxy collection crashes with Ansible versions 5.x and later. To downgrade Ansible to 4.10.0, use the following commands (also included as part of **netlab install grpc** script):

```
sudo pip3 install --upgrade ansible==4.10.0
```

* Inter-VRF route leaking is supported only in combination with BGP EVPN

(caveats-sros)=
## Nokia SR OS
* Only supported on top of *Containerlab*, using VRNetlab (VM running inside container)
* Requires the latest Ansible Galaxy collection 'nokia.grpc' and its dependencies to be installed from the git repo. You can also use the **netlab install grpc** command to install them

```
ansible-galaxy collection install git+https://github.com/nokia/ansible-networking-collections.git#/grpc/
python3 -m pip install grpcio protobuf==3.20.1
```

* As of September 2023, the Nokia Ansible Galaxy collection crashes with Ansible versions 5.x and later. To downgrade Ansible to 4.10.0, use the following commands (also included as part of **netlab install grpc** script):

```
sudo pip3 install --upgrade ansible==4.10.0
```

* OpenConfig support depends on a [pending PR](https://github.com/nokia/ansible-networking-collections/pull/21)

(caveats-vyos)=
## VyOS

**netlab** uses VyOS 1.4, which for now is a *rolling release* with daily builds (or custom builds).

This is because the stable release (*1.3*) lacks (or has limitations on) some of the nice features we are using such as MPLS, VRF/L3VPN, EVPN, ...

The use of a *rolling release* means potentially any build is broken or with regressions, even if the VyOS team is smart enough to perform some [automated smoke tests](https://github.com/vyos/vyos-1x/tree/current/smoketest/scripts/cli) and load [arbitrary configurations](https://github.com/vyos/vyos-1x/tree/current/smoketest/configs) to ensure there are no errors during config migration and system bootup.

Additionally, using always the latest build published on [Vagrant Hub](https://app.vagrantup.com/vyos/boxes/current), should allow to easily track and react to any configuration syntax change (which anyway is a very rare event). In any case, if you find a mis-alignment between the VyOS config and the **netlab** templates, feel free to *Open an Issue* or *Submit a PR*.

(vyos-clab)=
It looks like the official VyOS container is not updated as part of the daily builds; *netlab* uses a [third-party container](https://github.com/sysoleg/vyos-container) (`ghcr.io/sysoleg/vyos-container`) to run VyOS with *containerlab*.
