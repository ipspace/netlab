# Libvirt/KVM-based Lab on Linux VM or Bare-Metal Server

Building a *vagrant-libvirt*-based lab might take a bit longer than using Vagrant with Virtualbox, but the extra time is well worth the effort -- Vagrant *libvirt* plugin starts virtual machines in parallel (as opposed to *virtualbox* plugin which starts them in sequence), resulting in drastically reduced lab power-up time.

## Prerequisite Software Installation

Libvirt is a Linux-based virtualization management tool. To use it with Vagrant:

* Install KVM and libvirt
* Install Vagrant
* Install *vagrant-libvirt* plugin with **vagrant plugin install libvirt --plugin-version=0.4.1**

To simplify the installation process, use **netlab install** command to install Ansible, vagrant, libvirt, and all their prerequisites (tested on a Ubuntu 20.04 virtual machine):

```bash
$ netlab install ubuntu ansible libvirt
```

The *libvirt* installation scripts:

- Install all software packages required to use the *libvirt* Vagrant backend (including the *vagrant-libvirt* plugin)
- Adds current user to *libvirt* group
- Configures the *vagrant-libvirt* network

```{tip}
The installation scripts use **sudo** to install system software.
```

For more details, read *[A Quick Introduction to Netsim-Tools](https://blog.kirchne.red/netsim-tools-quickstart.html)* by [Leo Kirchner](https://www.linkedin.com/in/leo-kirchner/).

## Creating *vagrant-libvirt* Virtual Network

Vagrant *libvirt* provider connects management interfaces of managed VMs to *vagrant-libvirt* virtual network. Vagrant can figure out the device IP address based on dynamic DHCP mappings; *netsim-tools* can't. To make the Ansible inventory created by **[netlab create](../netlab/create.md)** tool work, your virtual network MUST include static DHCP bindings that map management MAC addresses defined in *netsim-tools* data model into expected IP addresses.

```{tip}
The _vagrant-libvirt_ virtual network is created as part of `netlab install libvirt` installation script.
```

The static DHCP bindings must map MAC addresses `08:4F:A9:00:00:xx` into IP addresses `192.168.121.1xx`. The easiest way to create the virtual network and static DHCP mappings is to use the `netsim/templates/provider/libvirt/vagrant-libvirt.xml` file supplied with *netsim-tools*:

* If needed, delete the existing *vagrant-libvirt* network with **virsh net-destroy vagrant-libvirt** and **virsh net-undefine vagrant-libvirt**
* Create the management network with **virsh net-create _path_/vagrant-libvirt.xml**

You could also use **virsh net-edit _vagrant-libvirt_** to edit the XML definition of your existing *vagrant-libvirt* network -- replace the exiting **ip** element with this XML snippet:

```
<ip address='192.168.121.1' netmask='255.255.255.0'>
	<dhcp>
	  <range start='192.168.121.2' end='192.168.121.99'/>
	  <host mac='08:4F:A9:00:00:01' ip='192.168.121.101'/>
	  <host mac='08:4F:A9:00:00:02' ip='192.168.121.102'/>
	  <host mac='08:4F:A9:00:00:03' ip='192.168.121.103'/>
	  <host mac='08:4F:A9:00:00:04' ip='192.168.121.104'/>
	  <host mac='08:4F:A9:00:00:05' ip='192.168.121.105'/>
	  <host mac='08:4F:A9:00:00:06' ip='192.168.121.106'/>
	  <host mac='08:4F:A9:00:00:07' ip='192.168.121.107'/>
	  <host mac='08:4F:A9:00:00:08' ip='192.168.121.108'/>
	  <host mac='08:4F:A9:00:00:09' ip='192.168.121.109'/>
	  <host mac='08:4F:A9:00:00:10' ip='192.168.121.110'/>
	  <host mac='08:4F:A9:00:00:11' ip='192.168.121.111'/>
	</dhcp>
</ip>
```

For more details, see [Using Libvirt Provider with Vagrant](https://codingpackets.com/blog/using-the-libvirt-provider-with-vagrant/) by [Brad Searle](https://www.linkedin.com/in/bradleysearle/). 

## Testing the Installation

The easiest way to test your installation is to use **[netlab test](../netlab/test.md)** command. If you prefer to do step-by-step tests, you might find this recipe useful:

* Create an empty directory and `topology.yml` file with the following contents within that directory:

```
---
defaults:
  device: cumulus

nodes: [ s1, s2, s3 ]
links: [ s1-s2, s2-s3, s1-s2-s3 ]
```

* Create Vagrantfile with `netlab create` command
* Execute `vagrant up` to spin up three Cumulus VX virtual machines
* Connect to the Cumulus VX devices with `vagrant ssh`
* Destroy the lab with `vagrant destroy -f`

## Creating Vagrant Boxes

Vagrant relies on *boxes* (prepackaged VM images), and while it's possible to download some network device images from Vagrant Cloud, you'll have to build most of the boxes you'd want to use in your lab.

The Vagrant boxes should have the following names:

| Virtual network device | Vagrant box name   |
|------------------------|--------------------|
| Arista vEOS            | arista/veos        |
| Arrcus ArcOS           | arcos/arcos4.1.1   |
| Cisco IOSv             | cisco/iosv         |
| Cisco CRS 1000v        | cisco/csr1000v     |
| Cisco Nexus 9300v      | cisco/nexus9300v   |
| Cumulus VX             | CumulusCommunity/cumulus-vx |
| Juniper vSRX 3.0       | juniper/vsrx3      |

The only box currently available on Vagrant Cloud is the Cumulus VX box. Vagrant automatically downloads it whenever you use Cumulus VX in your lab topology.

### Mutating Virtualbox Boxes

Cisco Nexus 9300v and Arista vEOS are available as Virtualbox boxes. To use them with *vagrant-libvirt*:

* Install Vagrant *mutate* plugin with **vagrant plugin install vagrant-mutate**
* Download the box file from vendor web site
* Install *virtualbox* version of the box file with **vagrant box add *filename* \-\-name _boxname_**
* Transform *virtualbox* box into *libvirt* box with **vagrant mutate _boxname_ libvirt**
* Remove the _virtualbox_ box with **vagrant box remove _boxname_ \-\-provider virtualbox** command.

### Building Your Own Boxes

[Brad Searle](https://codingpackets.com) published box-building recipes for the following platforms:

* [Cisco IOSv](https://codingpackets.com/blog/cisco-iosv-vagrant-libvirt-box-install/)
* [Cisco CSR](https://codingpackets.com/blog/cisco-csr-1000v-vagrant-libvirt-box-install/)
* [Arista vEOS](https://codingpackets.com/blog/arista-veos-vagrant-libvirt-box-install/) [[notes](#notes-on-arista-eos-vagrant-libvirt-box)]
* [Juniper vSRX 3.0](https://codingpackets.com/blog/juniper-vsrx3-0-vagrant-libvirt-box-install/) [[notes](#notes-on-juniper-vsrx-vagrantfile-template)]

Pete Crocker published similar recipe for [Fortinet firewalls](https://blog.petecrocker.com/post/fortinet_vagrant_libvirt/) (not yet supported by *netsim-tools*, PR welcome).

**Notes:**

* If you're experiencing high CPU utilization with Cisco CSR, [set halt_poll_ns to zero](https://codingpackets.com/blog/kvm-host-high-cpu-fix/).
* For more Vagrant details, watch the *[Network Simulation Tools](https://my.ipspace.net/bin/list?id=NetTools#SIMULATE)* part of *[Network Automation Tools](https://www.ipspace.net/Network_Automation_Tools)* webinar.

### Notes on Arista EOS *vagrant-libvirt* Box

You could use the *virtualbox* Arista EOS box and mutate it into a *libvirt* box, but the latest version of Arista vEOS available as Vagrant box for VirtualBox is 4.21.14M.

I used the [recipe published by Brad Searle](https://codingpackets.com/blog/arista-veos-vagrant-libvirt-box-install/) and modified it slightly to make it work flawlessly with EOS 4.25.0. After applying Brad's initial configuration (**do not** configure his event handlers), execute these commands to generate PKI key and certificate:

```
security pki key generate rsa 2048 default
security pki certificate generate self-signed default key default ↩
  param common-name Arista
```

After generating PKI certificate add these configuration commands to enable NETCONF and RESTCONF

```
management api http-commands
 no shutdown
!
management api netconf
 transport ssh default
!
management api restconf
 transport https default
  ssl profile default
  port 6040
!
management security
 ssl profile default
  certificate default key default
```

Finally, remove custom shell from *vagrant* user with

```
no user vagrant shell
```

Vagrant will be totally confused when it sees something that looks like a Linux box but doesn't behave like one, so add these commands to Vagrantfile (already included in `eos-domain.j2` template):

```
config.ssh.shell = "bash"
config.vm.guest = :freebsd
```

### Notes on Juniper vSRX Vagrantfile template

The Vagrant template for vSRX uses _default\_prefix_ libvirt parameter to set the domain (VM) name and uses the VM name to set libvirt vCPU quota.

The template has been tested with Vagrant version 2.2.14. Some earlier versions of Vagrant generated VM names using a slightly different algorithm (the underscore between _default\_prefix_ and VM name was added automatically) and might thus generate an unexpected VM name. To fix that problem remove parts of **vsrx-domain.j2** template:

* Remove _domain.default\_prefix_ parameter (default value should generate the expected VM name) or
* Remove the whole CPU-limiting logic (trading CPU cycles for simplicity)

### Notes on Arrcus ArcOS *vagrant-libvirt* Box and Ansible Collections

Please reach out to your Arrcus Customer Engineering Representative or [Contact Arrcus](https://www.arrcus.com/contact-us) for access to the Arrcus Vagrant Box file and ArcOS Ansible collections.

