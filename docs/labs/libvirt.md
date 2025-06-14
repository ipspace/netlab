(lab-libvirt)=
# Using libvirt/KVM with Vagrant

*netlab* uses *Vagrant* with the *vagrant-libvirt* plugin to start virtual machines in the libvirt/KVM environment.

To use libvirt/KVM environment on a Linux bare-metal server or a Linux VM:

* Install *netlab* ([Linux server](../install/linux.md), [Ubuntu virtual machine](../install/ubuntu-vm.md))
* If you're using Ubuntu, execute **netlab install libvirt** to install KVM, libvirt, Vagrant, and vagrant-libvirt. You'll have to install the software manually on other Linux distributions.
* [Download or build Vagrant boxes](#vagrant-boxes)
* Create [lab topology file](../topology-overview.md). *libvirt* is the default virtualization provider and does not have to be specified in the topology file
* [Fix the installation checks](libvirt-probes) if you're not using Ubuntu or Debian.
* Start the lab with **[netlab up](../netlab/up.md)**

```{warning}
You MUST use **netlab up** to start the lab to ensure the virtual machines get correct management IP addresses -- **netlab up** creates the [*vagrant-libvirt* management network](libvirt-mgmt) with predefined IP address range and DHCP bindings.
```

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Supported Versions

We tested _netlab_ with Vagrant version 2.4.0 and vagrant-libvirt plugin version 0.12.2. These are also the versions installed by the **netlab install libvirt** command.

(libvirt-vagrant-boxes)=
## Vagrant Boxes

Vagrant starts virtual machines from prepackaged VM images called *boxes*. While it's possible to download some network device images from Vagrant Cloud, you'll have to build most of the boxes you'd want to use in your lab.

You have to use the following box names when installing or building the Vagrant boxes (see [supported platforms](../platforms.md) and **[netlab show images](../netlab/show.md)** for more details):

| Virtual network device | Vagrant box name            |
| ---------------------- | --------------------------- |
| Arista vEOS            | arista/veos                 |
| Aruba CX               | aruba/cx                    |
| Cisco ASAv             | cisco/asav                  |
| Cisco Catalyst 8000v   | cisco/cat8000v              |
| Cisco CRS 1000v        | cisco/csr1000v              |
| Cisco IOSv             | cisco/iosv                  |
| Cisco IOSvL2           | cisco/iosvl2                |
| Cisco IOS XR           | cisco/iosxr                 |
| Cisco Nexus 9300v      | cisco/nexus9300v            |
| Cumulus VX 5.0 (NVUE)  | CumulusCommunity/cumulus-vx |
| Dell OS10              | dell/os10                   |
| Fortinet FortiOS       | fortinet/fortios            |
| Juniper vPTX (vJunos EVO) | juniper/vptx             |
| Juniper vSRX 3.0       | juniper/vsrx3               |
| [Linux](linux.md)      | generic/ubuntu2004          |
| Mikrotik RouterOS 6    | mikrotik/chr                |
| Mikrotik RouterOS 7    | mikrotik/chr7               |
| Sonic                  | netlab/sonic                |

The following Vagrant boxes are automatically downloaded from Vagrant Cloud when you're using them for the first time in your lab topology:

| Virtual network device | Vagrant box name   |
|------------------------|--------------------|
| Cumulus VX             | CumulusCommunity/cumulus-vx:4.4.0 |
| Generic Linux          | generic/ubuntu2004 |
| VyOS                   | vyos/current       |

**NOTES**:

* Even if a new box version is available from Vagrant Cloud, Vagrant will only output a warning to let the user know an update is available. You can ignore that warning or update the box with `vagrant box update`. 
* Vagrant does not automatically download the updated boxes because boxes can be relatively large (See [Vagrant box versioning](https://developer.hashicorp.com/vagrant/docs/boxes/versioning) for details).
* We recommend that you periodically download the updated box for `vyos/current`

(libvirt-build-boxes)=
### Building Vagrant Boxes

These documents contain box-building recipes using the **netlab libvirt** utility:

* [Arista vEOS](eos.md)
* [Aruba CX](arubacx.md)
* [Cisco ASAv](asav.md)
* [Cisco Catalyst 8000v](cat8000v.md)
* [Cisco CSR 1000v](csr.md)
* Cisco [IOSv](iosv.md) and [IOSvL2](iosvl2.md)
* [Cisco IOS XR](iosxr.md)
* [Cisco Nexus OS](nxos.md)
* [Cumulus Linux 5.x](cumulus_nvue.md)
* [Dell OS10](dellos10.md) by [Stefano Sasso](http://stefano.dscnet.org)
* [Fortinet FortiOS](fortios.md) - instructions based on the [work](https://blog.petecrocker.com/post/fortinet_vagrant_libvirt/) by [Pete Crocker](https://blog.petecrocker.com/about/) for 6.x/7.0 and updated for 7.4/7.6 in this [blog post](https://noodleops.space/2025-06/add-a-fortigate-in-your-virtual-lab-from-qcow-to-netlab-by-creating-a-vagrant-box/) by [Seb d'Argoeuves](https://noodlesops.space/about/).
* [Juniper vPTX](vptx.md)
* [Juniper vSRX 3.0](vsrx.md)
* [Mikrotik RouterOS 7](routeros7.md) - based on the original [Mikrotik RouterOS](http://stefano.dscnet.org/a/mikrotik_vagrant/) by [Stefano Sasso](http://stefano.dscnet.org)
* [Sonic](sonic.md)
* [VyOS](https://github.com/ssasso/packer-vyos-vagrant) by [Stefano Sasso](http://stefano.dscnet.org) - if you don't want to use the one from Vagrant Cloud.

```{note}
For more Vagrant details, watch the *[Network Simulation Tools](https://my.ipspace.net/bin/list?id=NetTools#SIMULATE)* part of *[Network Automation Tools](https://www.ipspace.net/Network_Automation_Tools)* webinar.
```

(libvirt-vm-settings)=
### Modifying VM Settings

The following node parameters influence the VM configuration created by *vagrant-libvirt*:

* **cpu** -- number of virtual CPUs allocated to the VM
* **memory** -- VM memory (in MB)
* **libvirt.nic_model_type** -- VM NIC model (example: e1000). Default _netlab_ settings usually work fine.
* **libvirt.nic_adapter_count** -- maximum number of VM NICs (default: 8)
* **libvirt.uuid** -- sets the libvirt VM UUID (some devices use the UUID to create their serial numbers). The value of this parameter is not checked[^UUID].

[^UUID]: In other words, you're on your own. After starting a lab, you can get a valid VM UUID with **virsh dumpxml _vm_name_|grep uuid** command (use **netlab status** to display the VM name).

(libvirt-box-replace)=
### Replacing Vagrant Boxes

If you want to rebuild and install a Vagrant box with the same version number, you must manually remove the old box. You must also delete the corresponding volume (disk image) from the *libvirt* storage pool (the *vagrant-libvirt* plugin installs new boxes but does not clean up the old ones).

To delete an old version of a Vagrant box, use a procedure similar to the one described below:

* Use `vagrant box list` to list the installed boxes
* Use `vagrant box remove <box-name> --box-version=<box-version>` to delete the Vagrant box[^VV]
* Use `virsh vol-list --pool default`[^DP] to list the installed Vagrant boxes
* Find the relevant volume name, for example, `cisco-VAGRANTSLASH-iosxr_vagrant_box_image_7.4.2_box.img` for an IOS XR 7.4.2 image
* Delete the volume with `virsh vol-delete --pool default <volume-name>`

[^VV]: You don't have to specify the box version unless you created multiple versions of the same box.

[^DP]: *libvirt* environment created with the **netlab install libvirt** installation script uses the *default* storage pool. A custom installation might use a different storage pool name.

The new Vagrant box will be copied into the *libvirt* storage pool the next time you use the affected device in your lab.

(libvirt-network)=
## Libvirt Networking

*netlab* uses *libvirt* networks and P2P UDP tunnels to implement topology links:

* P2P UDP tunnels are used for links with two nodes, and link **type** is set to **p2p** (the default behavior for links with two nodes). P2P tunnels are transparent; you can run any layer-2 control-plane protocol (including LACP) over them.
* *libvirt* networks are used for all other links. They are automatically created and deleted by **vagrant up** and **vagrant down** commands executed by **netlab up** and **netlab down**. **netlab up** sets the `group_fwd_mask` for all Vagrant-created Linux bridges to 0x4000 to [enable LLDP passthrough](https://blog.ipspace.net/2020/12/linux-bridge-lldp.html).
* *netlab* configures the MTU for libvirt bridge networks with a fixed value of 9500

(libvirt-capture)=
### Packet Capture

The *libvirt* point-to-point UDP tunnels are not implemented as Linux interfaces, making it impossible to start packet capture on the VM interfaces attached to point-to-point tunnels. The VMs must be attached to Linux bridges for the **[netlab capture](netlab-capture)** command to work.

Add **type: lan** to a point-to-point link between two virtual machines to change its implementation into a Linux bridge. You can also set the **defaults.providers.libvirt.p2p_bridge** parameter to *True* if you don't want to use UDP tunnels for point-to-point links (see [](defaults-topology) and [](defaults-user-file) for more information on changing system defaults).

Finally, you could start the lab with the `netlab up -p libvirt:p2p_bridge` command to change the system default for a single lab instance.

(libvirt-network-external)=
### Connecting to the Outside World

Lab networks are created as private, very-isolated *libvirt* networks without a DHCP server. If you want a lab network connected to the outside world, set the **libvirt.public** and/or **libvirt.uplink** link attributes (setting one of them is enough):

* Set **libvirt.public** link attribute to **true**, or to any value [supported by *libvirt*](https://libvirt.org/formatdomain.html#direct-attachment-to-physical-interface)[^MACVTAP].
* Set **libvirt.uplink** link attribute to the name of one of the Ethernet interfaces on your server[^IFNAME] if your Linux distribution does not use **eth0** as the name of the Ethernet interface[^U22].

[^MACVTAP]: The default value for the **libvirt.public** attribute is **bridge** which creates a *[macvtap](https://virt.kernelnewbies.org/MacVTap)* interface for every node connected to the link.

Example: use the following topology to connect your lab to the outside world through `r1` on a Linux server that uses `enp86s0` as the name of the Ethernet interface:

```
defaults.device: cumulus
nodes: [ r1,r2 ]
links:
- r1-r2
- r1:
  libvirt:
    uplink: enp86s0
```

[^IFNAME]: Use **ip addr** or **ifconfig** find the interface name.

[^U22]: Example: Ubuntu 22.04 uses weird interface names based on the underlying NIC type.

Finally, if you want to connect the management network to the outside world, create the management network [based on an existing Linux bridge](libvirt-mgmt) that is already connected to the outside world or enable port forwarding.

### Using Existing Libvirt Networks

To attach lab devices to existing *libvirt* virtual networks:

* Set the link **bridge** attribute to the name of an existing network.
* Set the link **libvirt.permanent** attribute to **True** to tell *vagrant-libvirt* plugin it should not destroy the network on shutdown.

You can use this functionality to attach lab devices to public networks or networks extended with VXLAN transport.

```{warning}
**vagrant destroy** command will crash if it tries to destroy an existing non-persistent *libvirt* network, stopping the **netlab down** procedure. Rerun the **netlab down** command to complete the lab shutdown/cleanup process.
```

(libvirt-mgmt)=
### Libvirt Management Network

*vagrant-libvirt* plugin uses a dedicated *libvirt* network to connect the VM management interfaces to the host TCP/IP stack. **netlab up** command creates that network before executing **vagrant up** to ensure the network contains the expected DHCP mappings. The management network is automatically deleted when you execute **netlab down** (recommended) or **vagrant destroy**.

You can change the parameters of the management network in the **addressing.mgmt** pool:

* **ipv4**: The IPv4 prefix used for the management network (default: `192.168.121.0/24`)
* **ipv6**: Optional IPv6 management network prefix. It's not set by default.
* **start**: The offset of the first VM management IP address in the management network (default: `100`). For example, with **start** set to 50, the device with **node.id** set to 1 will get the 51st IP address in the management IP prefix.
* **\_network**: The *libvirt* network name (default: `vagrant-libvirt`)
* **\_bridge**: The name of the underlying Linux bridge (default: `libvirt-mgmt`)
* **\_permanent**: set to `True` to use an existing *libvirt* network as the management network. **netlab up** will create the network if it does not exist and tell Vagrant not to remove it when the lab is stopped.

**Important caveats:**

* **netlab up** uses XML definition in `templates/provider/libvirt/vagrant-libvirt.xml` within the Python package directory ([source file](https://github.com/ipspace/netlab/blob/master/netsim/templates/provider/libvirt/vagrant-libvirt.xml)) to create the management network. If you'd like to change the management network parameters, create a custom XML definition in the `libvirt/vagrant-libvirt.xml` file in the current directory, `~/.netlab` directory, or `/etc/netlab` directory.
* If you want to use an existing libvirt network as the management network, make sure it has the same static DHCP mappings as the management network created by the **netlab up** command.

(libvirt-mgmt-ip)=
### VM Management IPv4 Addresses

The only way to assign a management IPv4 address to a network device started as a virtual machine is through DHCP, and *vagrant*, together with *libvirt* (and *dnsmasq*), provides a seamless implementation. IPv6 management addresses do not work as most Vagrant boxes do not use DHCPv6.

*netlab* creates static DHCP mappings in the management network ([see above](libvirt-mgmt)) and asks *vagrant-libvirt* to set the MAC address of the VM management interface to a well-known value, ensuring that each VM gets the expected management IPv4- and MAC address assigned by *netlab* based on the [device node ID](node-augment) and the **[start](address-pool-specs)** parameter of the [**mgmt** address pool](../addressing.md).

You can change the IPv4 address of a device's management interface with the **mgmt.ipv4** node parameters to have fixed management IPv4 addresses for your virtual machines (for example, to be accessed from an external management tool or to match an existing deployment). However, it is recommended to use the auto-generated IPs, which are guaranteed to not overlap.

(libvirt-port-forwarding)=
### Port Forwarding

*netlab* supports *vagrant-libvirt* port forwarding -- mapping of TCP ports on VM management IP address to ports on the host. You can use port forwarding to access the lab devices via the host's external IP address without exposing the management network to the outside world.

Port forwarding is turned off by default and can be enabled by configuring the **defaults.providers.libvirt.forwarded** dictionary. Dictionary keys are TCP port names (`ssh`, `http`, `https`, or `netconf`), and dictionary values are the start values of host ports. *netlab* assigns a unique host port to every VM forwarded port based on the start value and VM node ID.

For example, when given the following topology...

```
defaults.providers.libvirt.forwarded:
  ssh: 2000

defaults.device: cumulus
nodes:
  r1:
  r2:
    id: 42
```

... *netlab* maps:
    
* SSH port on management interface of R1 to host port 2001 (R1 gets default node ID 1)
* SSH port on management interface of R2 to host port 2042 (R2 has static ID 42)

## Starting Virtual Machines in Batches

*vagrant-libvirt* plugin tries to start all virtual machines specified in `Vagrantfile` in parallel. The resulting strain on CPU resources might cause VM boot failures in large topologies. As a workaround, you can configure **libvirt** virtualization provider to execute a series of `vagrant up` commands to start the virtual machines in smaller batches:

* Configure the batch size with **defaults.providers.libvirt.batch_size** parameter (an integer between 1 and 50)
* Configure idle interval between batches (if needed) with **defaults.providers.libvirt.batch_interval** parameter (between 1 and 1000 seconds).

Example:

```
provider: libvirt
defaults.device: cumulus
defaults.providers.libvirt.batch_size: 2
defaults.providers.libvirt.batch_interval: 10

nodes: [ a,b,c,x,z ]
module: [ ospf ]

links: [ a-x, a-z, b-x, b-z, c-x, c-z ]
```

Please note that the `batch_size` is set artificially low to ensure this small lab topology generates three batches. Realistic `batch_size` depends on your hardware resources (CPU, memory) and VM type.

You can use the [netlab environment variables](defaults-env) to set the batch sizes without changing lab topology or _netlab_ defaults, for example:

```
$ export NETLAB_PROVIDERS_LIBVIRT_BATCH__SIZE=2
$ export NETLAB_PROVIDERS_LIBVIRT_BATCH__INTERVAL=10
```

```{tip}
The virtual machines are batched based on their order in **‌nodes** list/dictionary. You might want to adjust the node order to group virtual machines with long start times (for example, Cisco Nexus OS or Juniper vSRX) into as few batches as possible.
```

(libvirt-probes)=
## Changing Installation Checks

**netlab up** executes a series of commands starting with `kvm-ok` to validate your KVM/libvirt/vagrant installation before trying to start the lab. These commands might fail on Linux distributions that do not include the `kvm-ok` command ([more details](linux-commands-mandatory)).

To make the installation checks work, install the `kvm-ok` command into the `/usr/sbin` directory. You can also modify (or turn off) the installation checks. The **libvirt** installation checks are specified in the **defaults.providers.libvirt.probe** list:

* To display them, use the **netlab show defaults providers.libvirt.probe** command.
* To turn off the probes, set the **defaults.providers.libvirt.probe** lab topology parameter to `[]`. Even better, change the [user defaults file](defaults-user-file), adding:

```
providers.libvirt.probe: []
```

```{eval-rst}
.. toctree::
   :caption: Box Building Recipes
   :maxdepth: 1
   :hidden:

   libvirt-box-caveats.md
   eos.md
   arubacx.md
   asav.md
   cat8000v.md
   csr.md
   cumulus_nvue.md
   fortios.md
   iosv.md
   iosvl2.md
   iosxr.md
   nxos.md
   dellos10.md
   vsrx.md
   vptx.md
   linux.md
   routeros7.md
   sonic.md
..
```
