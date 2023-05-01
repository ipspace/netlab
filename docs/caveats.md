# Platform Caveats

## Cisco IOSv

* Cisco IOSv release 15.x does not support unnumbered interfaces. Use Cisco CSR 1000v.

(caveats-iosxr)=
## Cisco IOS XRv

* netlab was tested with IOS XR release 7.4. Earlier releases might use a different management interface name, in which case you'll have to set **defaults.devices.iosxr.mgmt_if** parameter to the name of the management interface
* Copying Vagrant public insecure SSH key into IOS XR during the box building process is cumbersome. Vagrant configuration file uses fixed SSH password.
* Maximum interface bandwidth on IOS XRv is 1 Gbps (1000000).

(caveats-csr)=
## Cisco CSR 1000v

* Cisco CSR 1000v does not support interface MTU lower than 1500 bytes or IP MTU higher than 1500 bytes.
* VLAN subinterfaces can be configured on Cisco CSR 1000v but do not work. CSR 1000v cannot be used as a router-on-a-VLAN-trunk device.

## Cisco Nexus OS

* Nexus OS release 9.3 runs in 6 GB of RAM (*netlab* system default).
* Nexus OS release 10.1 requires 8 GB of RAM and will fail with a cryptic message claiming it's running on unsupported hardware when it doesn't have enough memory.
* Nexus OS release 10.2 requires at least 10 GB of RAM and crashes when ran as an 8 GB VM.
* To change the default amount of memory used by a **nxos** device, set the **defaults.devices.nxos.memory** parameter (in MB)[^DD]

[^DD]: See [](topology/hierarchy.md) for an in-depth explanation of why attributes with hierarchical names work in *netlab*

## Cumulus Linux in ContainerLab

* *containerlab* could run Cumulus Linux as a [container or as a micro-VM with *firecracker*](https://containerlab.dev/manual/kinds/cvx/). The default used by *netlab* is to run Cumulus Linux as a container. To change that, add **clab.runtime** parameter to node data.
* Cumulus Linux ran as a container might report errors related to DHCP client during initial configuration, in which case you might have to disable **apparmor** for DHCP client to get it to run. The hammer-of-Thor command to fix this problem is `sudo systemctl disable apparmor` followed by a reboot, your sysadmin friends probably have a better suggestion.
* *netlab* uses Cumulus VX containers created by Michael Kashin and downloaded from his Docker Hub account. Once Nvidia releases an official container image, change the container name with **defaults.devices.cumulus.clab.image**[^DD] parameter (or by editing the `topology-defaults.yml` file included with *netlab*).
* The Cumulus VX 4.4.0 Vagrant box for VirtualBox is broken. *netlab* is using Cumulus VX 4.3.0 with *virtualbox* virtualization provider.

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

## Fortinet FortiOS

* *FortiOS* VM images by default have a 15 day evaluation license. The VM has [limited capabilities](https://docs.fortinet.com/document/fortigate-private-cloud/6.0.0/fortigate-vm-on-kvm/504166/fortigate-vm-virtual-appliance-evaluation-license) without a license file. It will work for 15 days from first boot, at which point you must install a license file or recreate the vagrant box completely from scratch.
* Ansible automation of FortiOS requires the installation of the [FortiOS Ansible Collection 2.1.3 or greater](https://galaxy.ansible.com/fortinet/fortios) and a FortiOS version > 6.0.

(caveats-frr-config)=
## FRR

* Many FRR configuration templates are not idempotent -- you cannot run **netlab initial** multiple times. Non-idempotent templates include VLAN and VRF configurations.

## Generic Linux

*Generic Linux device* is a Linux VM running Ubuntu 20.04 or an Alpine/Python container. To use any other Linux distribution, add **image** attribute with the name of Vagrant box or Docker container to the node data[^GL]; the only requirements are working Python environment (to support Ansible playbooks used in **netlab initial** command) and the presence of **ip** command used in initial device configuration.

[^GL]: You can also set the **defaults.devices.linux._provider_.image** attribute to change the Vagrant box for all Linux hosts in your lab.

### Host Routing

Generic Linux device is an IP host that does not support IP forwarding or IP routing protocols. It uses static routes set up as follows:

* IPv4 default route points to Vagrant management interface (set by Vagrant/DHCP).
* IPv6 default route points to whichever adjacent device is sending IPv6 Route Advertisement messages (default Linux behavior).
* IPv4 static routes for all IPv4 address pools defined in lab topology point to the first neighbor on the first non-management interface.

**Corollary:** Linux devices SHOULD have a single P2P link to an adjacent network device. If you encounter problems using any other lab topology, please submit a Pull Request fixing it instead of complaining ;)

### LLDP

* LLDP on Generic Linux is started in Ubuntu VMs but not in Alpine containers.

## Mikrotik RouterOS 6

* In runs with the *CHR* image.
* LLDP on Mikrotik CHR RouterOS is enabled on all the interfaces.

## Mikrotik RouterOS 7

* In runs with the *CHR* image.
* LLDP on Mikrotik CHR RouterOS is enabled on all the interfaces.
* At the time of the build, testing is being performed with releases **7.5** (claimed as *stable*) and **7.6beta8**. On both of them:
  * MPLS dataplane seems to have issues when using *virtio* networking, while the LDP and VPNv4 control plane work fine. With *e1000* everything works fine.
  * BGP-based route leaking is working on the control plane, but not on the dataplane.

## Nokia SR Linux
* Only supported on top of *Containerlab*
* Supports container image release 23.3.1 or later (due to YANG model changes)
* Requires the latest Ansible Galaxy collection 'nokia.grpc' and its dependencies to be installed, from the git repo:
```
ansible-galaxy collection install git+https://github.com/nokia/ansible-networking-collections.git#/grpc/
python3 -m pip install grpcio protobuf==3.20.1
```

## Nokia SR OS
* Only supported on top of *Containerlab*, using VRNetlab (VM running inside container)
* Requires the latest Ansible Galaxy collection 'nokia.grpc' and its dependencies to be installed, from the git repo:
```
ansible-galaxy collection install git+https://github.com/nokia/ansible-networking-collections.git#/grpc/
python3 -m pip install grpcio protobuf==3.20.1
```
* OpenConfig support depends on a [pending PR](https://github.com/nokia/ansible-networking-collections/pull/21)

## VyOS

**netlab** uses VyOS 1.4, which for now is a *rolling release* with daily builds (or custom builds).

This is because the stable release (*1.3*) lacks (or has limitations on) some of the nice features we are using such as MPLS, VRF/L3VPN, EVPN, ...

The use of a *rolling release* means potentially any build is broken or with regressions, even if the VyOS team is smart enough to perform some [automated smoke tests](https://github.com/vyos/vyos-1x/tree/current/smoketest/scripts/cli) and load [arbitrary configurations](https://github.com/vyos/vyos-1x/tree/current/smoketest/configs) to ensure there are no errors during config migration and system bootup.

Additionally, using always the latest build published on [Vagrant Hub](https://app.vagrantup.com/vyos/boxes/current), should allow to easily track and react to any configuration syntax change (which anyway is a very rare event). In any case, if you find a mis-alignment between the VyOS config and the **netlab** templates, feel free to *Open an Issue* or *Submit a PR*.

(vyos-clab)=
It looks like the official VyOS container is not updated as part of the daily builds; *netlab* uses a [third-party container](https://github.com/sysoleg/vyos-container) (`ghcr.io/sysoleg/vyos-container`) to run VyOS with *containerlab*.

## Dell OS10

Dell OS10 uses a concept of a so-called *Virtual Network* interface to try to handle transparently VLANs and VXLANs in the same way. However, it seems that right now it is **NOT** possible to activate OSPF on a *Virtual Network* (VLAN) SVI interface.

Sadly, it's also **NOT** possible to use *VRRP* on a *Virtual Network* interface (but *anycast* gateway is supported). At the same time, *anycast* gateway is not supported on plain *ethernet* interfaces, so you need to use *VRRP* there.

## Juniper vMX in Containerlab
Juniper vMX runs in Containerlab with the *vrnetlab* extension. See [clab docs](https://containerlab.dev/manual/kinds/vr-vmx/) for further details.

Additionally, the Juniper vMX image in *vrnetlab* uses the network `10.0.0.0/24` for its own internal network, which conflicts with the default network used by **netlab** for the loopback addressing. For this reason it's better to use a different subnet for the loopback addresses of your topologies with:
```
addressing:
  loopback:
    ipv4: 10.255.0.0/24
  router_id:
    ipv4: 10.255.0.0/24
```

## Aruba AOS-CX

* Ansible automation of Aruba AOS-CX requires the installation of the [ArubaNetworks Ansible Collection](https://galaxy.ansible.com/arubanetworks/aoscx) with `ansible-galaxy collection install arubanetworks.aoscx`.
* OSPF processes can be only *1-63*. VRF indexes usually are > 100, so a device tweak will map every *vrfidx* to a different OSPF process id. That means you cannot have more than 62 VRF using OSPF.
* The VXLAN dataplane (at least, on the virtual version) seems not supporting VNI greater than 65535. If you set an higher value, an overflow will occur, and you may have overlapping VNIs. The workaround for this is to set, i.e., `defaults.vxlan.start_vni: 20000` (especially on multi-vendor topologies).
* On the Aruba AOS-CX Virtual version *10.11.0001*, EVPN Symmetric IRB seems not supported.
* On the Aruba AOS-CX Virtual version *10.11.0001*, MPLS L3VPN forwarding plane seems broken (while the control plane is working fine).
* Limitations of the Aruba AOS-CX Simulator can be found [here](https://feature-navigator.arubanetworks.com/), selecting *CX Simulator* as platform.
