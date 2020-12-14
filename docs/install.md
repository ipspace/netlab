# Installation

Installing the tools:

* Clone the [netsim-tools Github repository](https://github.com/ipspace/netsim-tools) (or the [netsim-examples repository](https://github.com/ipspace/netsim-examples/) which includes netsim-tools repository as a submodule.
* Install PyYAML and Jinja2 Python libraries with **pip install pyyaml jinja2** (these libraries are automatically installed if you decide to install Ansible).
* Optional: install Ansible or use [ipSpace network automation container image](https://hub.docker.com/r/ipspace/automation). The tools were tested with Ansible 2.9 and 2.10.

## Building Your Lab

The current version of the **config-generate** tool contains templates needed to create a Vagrant topology containing Cisco IOSv, Cisco CSR 1000v, Cisco Nexus 9300v, and Arista EOSv devices with *vagrant-libvirt* provider. The Vagrant templates were tested on Ubuntu 20.04; if your environment needs specific adjustments please submit a pull request.

If you're new to *libvirt*, read [Using Libvirt Provider with Vagrant](https://codingpackets.com/blog/using-the-libvirt-provider-with-vagrant/) blog post by [Brad Searle](https://www.linkedin.com/in/bradleysearle/).

The Vagrantfile templates for individual network devices were derived from the following *build your own Vagrant box for vagrant-libvirt environment* blog posts:

* [Cisco IOSv](https://codingpackets.com/blog/cisco-iosv-vagrant-libvirt-box-install/) (Brad Searle/codingpackets.com)
* [Cisco CSR](https://codingpackets.com/blog/cisco-csr-1000v-vagrant-libvirt-box-install/) (Brad Searle/codingpackets.com)
* [Arista EOSv](https://codingpackets.com/blog/arista-veos-vagrant-libvirt-box-install/) (Brad Searle/codingpackets.com)
* [Juniper vSRX 3.0](https://codingpackets.com/blog/juniper-vsrx3-0-vagrant-libvirt-box-install/) (Brad Searle/codingpackets.com)
* [Cisco Nexus 9300v](https://github.com/mweisel/cisco-nxos9kv-vagrant-libvirt) ([Marc Weisel](https://www.linkedin.com/in/marcweisel/))

For more Vagrant details, watch the *[Network Simulation Tools](https://my.ipspace.net/bin/list?id=NetTools#SIMULATE)* part of *[Network Automation Tools](https://www.ipspace.net/Network_Automation_Tools)* webinar.

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
