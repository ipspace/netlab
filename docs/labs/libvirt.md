# Using libvirt/KVM with Vagrant

*netlab* can use *Vagrant* with *vagrant-libvirt* plugin to start virtual machines in libvirt/KVM environment. To use it:

* Install *netlab* on a [Linux server](../install/linux.md) or [virtual machine](../install/ubuntu-vm.md)
* If you're using Ubuntu, execute **netlab install libvirt** to install KVM, libvirt, Vagrant, and vagrant-libvirt. You'll have to install the software manually on other Linux distributions.
* [Download or build Vagrant boxes](#vagrant-boxes)
* Create [lab topology file](../topology-overview.md). *libvirt* is the default virtualization provider and does not have to be specified in the topology file
* Start the lab with **[netlab up](../netlab/up.md)**

```{warning}
You MUST use **‌netlab up** to start the lab to ensure the virtual machines get correct management IP addresses.
```

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Vagrant Boxes

Vagrant starts virtual machines from prepackaged VM images called *boxes*. While it's possible to download some network device images from Vagrant Cloud, you'll have to build most of the boxes you'd want to use in your lab.

You have to use the following box names when installing or building the Vagrant boxes (see [supported platforms](../platforms.md) and **[netlab show images](../netlab/show.md)** for more details):

| Virtual network device | Vagrant box name            |
| ---------------------- | --------------------------- |
| Arista vEOS            | arista/veos                 |
| Cisco ASAv             | cisco/asav                  |
| Cisco IOSv             | cisco/iosv                  |
| Cisco CRS 1000v        | cisco/csr1000v              |
| Cisco Nexus 9300v      | cisco/nexus9300v            |
| Dell OS10              | dell/os10                   |
| Fortinet FortiOS       | fortinet/fortios            |
| Juniper vSRX 3.0       | juniper/vsrx3               |
| Mikrotik RouterOS 6    | mikrotik/chr                |
| Mikrotik RouterOS 7    | mikrotik/chr7               |

The following Vagrant boxes are automatically downloaded from Vagrant Cloud when you're using them for the first time in your lab topology:

| Virtual network device | Vagrant box name   |
|------------------------|--------------------|
| Cumulus VX             | CumulusCommunity/cumulus-vx:4.4.0 |
| Cumulus VX 5.0 (NVUE)            | CumulusCommunity/cumulus-vx:5.0.1 |
| Generic Linux          | generic/ubuntu2004 |
| VyOS                   | vyos/current       |

**NOTES**:

* Even if a new box version is available from Vagrant Cloud, Vagrant will only output a warning to let the user know an update is available. You can ignore that warning or update the box with `vagrant box update`. 
* Vagrant does not automatically download the updated boxes because boxes can be relatively large (See [Vagrant box versioning](https://developer.hashicorp.com/vagrant/docs/boxes/versioning) for details).
* We recommend that you periodically download the updated box for `vyos/current`

## Building Your Own Boxes

* [Arista vEOS](eos.md)
* [Cisco ASAv](asav.md)
* [Cisco IOSv](iosv.md)
* [Cisco CSR](csr.md)
* [Cisco Nexus OS](nxos.md)
* [Dell OS10](dellos10.md) by [Stefano Sasso](http://stefano.dscnet.org)
* [Fortinet FortiOS](https://blog.petecrocker.com/post/fortinet_vagrant_libvirt/) by [Pete Crocker](https://blog.petecrocker.com/about/)
* [Juniper vSRX 3.0](vsrx.md)
* [Mikrotik RouterOS 7](routeros7.md) - based on the original [Mikrotik RouterOS](http://stefano.dscnet.org/a/mikrotik_vagrant/) by [Stefano Sasso](http://stefano.dscnet.org)
* [VyOS](https://github.com/ssasso/packer-vyos-vagrant) by [Stefano Sasso](http://stefano.dscnet.org) - if you don't want to use the one from Vagrant Cloud.

```{note}
For more Vagrant details, watch the *[Network Simulation Tools](https://my.ipspace.net/bin/list?id=NetTools#SIMULATE)* part of *[Network Automation Tools](https://www.ipspace.net/Network_Automation_Tools)* webinar.
```

## Replacing Vagrant Boxes

If you want to rebuild and install a Vagrant box with the same version number, you have to remove the old box manually. You also have to delete the corresponding volume (disk image) from *libvirt* storage pool (*vagrant-libvirt* plugin installs new boxes but does not clean up the old ones).

To delete an old version of a Vagrant box use a procedure  similar to the one described below:

* Use `vagrant box list` to list the installed boxes
* Use `vagrant box remove <box-name> --box-version=<box-version>` to delete the Vagrant box[^VV]
* Use `virsh vol-list --pool default`[^DP] to list the installed Vagrant boxes
* Find the relevant volume name, for example, `cisco-VAGRANTSLASH-iosxr_vagrant_box_image_7.4.2_box.img` for an IOS XR 7.4.2 image
* Delete the volume with `virsh vol-delete --pool default <volume-name>`

[^VV]: You don't have to specify the box version unless you created multiple versions of the same box.

[^DP]: *libvirt* environment created with the **netlab install libvirt** installation script uses the *default* storage pool. A custom installation might use a different storage pool name.

The new Vagrant box will be copied into the *libvirt* storage pool the next time you'll use the affected device in your lab.

## Libvirt Management Network

*vagrant-libvirt* plugin a dedicated uses *libvirt* network to connect the VM management interfaces to the host TCP/IP stack. **netlab up** command creates that network before executing **vagrant up** to ensure the network contains desired DHCP mappings. The management network is automatically deleted when you execute **netlab down** (recommended) or **vagrant destroy**.

You can change the parameters of the management network in the **addressing.mgmt** pool:

* **ipv4**: The IPv4 prefix used for the management network (default: `192.168.121.0/24`)
* **\_network**: The *libvirt* network name (default: `vagrant-libvirt`)
* **\_bridge**: The name of the underlying Linux bridge (default: `libvirt-mgmt`)

## Starting Virtual Machines in Batches

*vagrant-libvirt* plugin tries to start all the virtual machines specified in `Vagrantfile` in parallel. The resulting strain on CPU resources might cause VM boot failures in very large topologies. As a workaround, you can configure **libvirt** virtualization provider to execute a series of `vagrant up` commands to start the virtual machines in smaller batches:

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

Please note that the `batch_size` is set artificially low so that this pretty small topology generates three batches. Realistic `batch_size` depends on your hardware resources (CPU, memory) and VM type.

```{tip}
The virtual machines are batched based on their order in **‌nodes** list/dictionary. You might want to adjust the node order to group virtual machines with long start times (example: Cisco Nexus OS or Juniper vSRX) into as few batches as possible.
```

```{eval-rst}
.. toctree::
   :caption: Box Building Recipes
   :maxdepth: 1
   :hidden:

   eos.md
   asav.md
   csr.md
   iosv.md
   nxos.md
   dellos10.md
   vsrx.md
   routeros7.md
..
```
