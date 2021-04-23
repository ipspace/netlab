# Installation

Installing the tools:

* Clone the [netsim-tools Github repository](https://github.com/ipspace/netsim-tools) (or the [netsim-examples repository](https://github.com/ipspace/netsim-examples/) which includes netsim-tools repository as a submodule.
* If needed, select the desired release with **git checkout _release-tag_**. Use **git tag** to get the list of release tags.
* Within the **netsim-tools** directory, install PyYAML, Jinja2, netaddr and python-box Python libraries with **pip3 install -r requirements.txt**.
* Optional: install Ansible or use [ipSpace network automation container image](https://hub.docker.com/r/ipspace/automation). The tools were tested with Ansible 2.9 and 2.10.

## Building Your Lab

The current version of the **config-generate** tool contains templates needed to create a Vagrant topology containing Cisco IOSv, Cisco CSR 1000v, Cisco Nexus 9300v, and Arista vEOS devices with *vagrant-libvirt* or *virtualbox* provider. The tool also supports container-based network operating systems powered by *containerlab*.

The Vagrant templates were tested on Ubuntu 20.04; if your environment needs specific adjustments please submit a pull request.

**Notes:**
* The only device tested with VirtualBox is Nexus 9300v ([more details](platforms.html#virtualbox-support-limitations))
* The only device tested with Containerlab is Arista cEOS

### Building a *libvirt*-based Lab

If you're new to *libvirt*, read [Using Libvirt Provider with Vagrant](https://codingpackets.com/blog/using-the-libvirt-provider-with-vagrant/) blog post by [Brad Searle](https://www.linkedin.com/in/bradleysearle/). 

The *vagrant-libvirt* network needs static DHCP bindings to ensure the network devices get consistent management IP addresses. See *[creating vagrant-libvirt network](#creating-vagrant-libvirt-network)* for details.

The Vagrantfile templates for individual network devices were derived from the following *build your own Vagrant box for vagrant-libvirt environment* blog posts:

* [Cisco IOSv](https://codingpackets.com/blog/cisco-iosv-vagrant-libvirt-box-install/) (Brad Searle/codingpackets.com)
* [Cisco CSR](https://codingpackets.com/blog/cisco-csr-1000v-vagrant-libvirt-box-install/) (Brad Searle/codingpackets.com)
* [Arista vEOS](https://codingpackets.com/blog/arista-veos-vagrant-libvirt-box-install/) (Brad Searle/codingpackets.com) [[notes](#notes-on-arista-eos-vagrant-libvirt-box)]
* [Juniper vSRX 3.0](https://codingpackets.com/blog/juniper-vsrx3-0-vagrant-libvirt-box-install/) (Brad Searle/codingpackets.com) [[notes](#notes-on-juniper-vsrx-vagrantfile-template)]
* [Cisco Nexus 9300v](https://github.com/mweisel/cisco-nxos9kv-vagrant-libvirt) ([Marc Weisel](https://www.linkedin.com/in/marcweisel/))

**Notes:**

* Nexus 9300v takes almost exactly a minute after SSH becomes available on the management interface to "boot" the Ethernet linecard (module 1) and activate Ethernet interfaces. Leave it alone for a while even when Vagrant tells you the VM is ready.
* If you're experiencing high CPU utilization with Cisco CSR, [set halt_poll_ns to zero](https://codingpackets.com/blog/kvm-host-high-cpu-fix/).
* For more Vagrant details, watch the *[Network Simulation Tools](https://my.ipspace.net/bin/list?id=NetTools#SIMULATE)* part of *[Network Automation Tools](https://www.ipspace.net/Network_Automation_Tools)* webinar.

### Creating vagrant-libvirt Network

Vagrant *libvirt* provider connects management interfaces of managed VMs to *vagrant-libvirt* virtual network. Vagrant can figure out the device IP address based on dynamic DHCP mappings; **netsim-tools** can't. To make the Ansible inventory created by **create-topology** tool work your virtual network MUST include static DHCP bindings that map MAC addresses used by **create-topology** into expected IP addresses.

The easiest way to create the management network is to use the XML file `netsim/templates/provider/libvirt/vagrant-libvirt.xml`
:

* If needed, delete the existing *vagrant-libvirt* network with **virsh net-destroy vagrant-libvirt**
* Create the management network with **virsh net-create *path*/vagrant-libvirt.xml**

You could also add DHCP bindings to your existing *vagrant-libvirt* network; here's the XML definition:

```
<network>
  <name>vagrant-libvirt</name>
  <forward mode='nat'>
    <nat>
      <port start='1024' end='65535'/>
    </nat>
  </forward>
  <bridge name='virbr1' stp='on' delay='0'/>
  <mac address='52:54:00:d8:3f:0d'/>
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
</network>
```

### Notes on Arista EOS *vagrant-libvirt* Box

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

