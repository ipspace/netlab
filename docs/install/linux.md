(install-linux-server)=
# Running *netlab* on a Linux Server

This page describes generic installation steps for creating a virtual lab environment on any Linux distribution ([follow these instructions](ubuntu.md) if you plan to run your labs on an Ubuntu server).

```{warning}
We test _netlab_ on Ubuntu to ensure we provide a reasonably hassle-free experience to networking engineers without Linux sysadmin skills. Unfortunately, we cannot help you if you run _netlab_ on another Linux distribution (dealing with one distro is more than enough pain). Still, please try to make it work; we would appreciate it if you could add your findings to this document. Thank you!
```

## Prerequisite Software Installation

*netlab* is a Python package that uses KVM to run virtual machines and Docker to run containers. Virtual machines in the KVM environment and the associated Linux bridges are created with Vagrant using libvirt API. Ansible is used to configure the network devices.

![netlab on Linux](linux-architecture.png)

To build a Linux environment needed to run network devices as virtual machines or containers:

* Install Python 3.8 or later (use the latest Python version supported by your Linux distribution)
* Install Ansible 2.9.1 or later and any Ansible networking dependencies (example: paramiko)

```{warning}
At the moment, _netlab_ does not work with Ansible release 12.x. Install the latest Ansible 11.x release.
```

If you want to run network devices as virtual machines with KVM:

* Install KVM and libvirt
* Install Vagrant 2.4.3 or later[^CSV]
* Install *vagrant-libvirt* plugin with `vagrant plugin install libvirt --plugin-version=0.12.2`

If you want to run network devices as containers (or virtual machines in *vrnetlab* containers), install Docker and containerlab.

[^CSV]: We must change the recommended Vagrant release every few months. Please check the [libvirt installation script](https://github.com/ipspace/netlab/blob/dev/netsim/install/libvirt.sh) for details.

(linux-commands-mandatory)=
*netlab* also needs (at least) these Linux commands to provide its full functionality:

* **ssh** to connect to the virtual machines.
* **sshpass** to pass admin passwords to **ssh** (we're not brave enough to believe SSH keys work on all network devices).
* **ansible-playbook** to configure network devices
* **kvm-ok** to test if KVM works on the server[^KVMOK] (but see also [](libvirt-probes))
* **virsh** to create libvirt networks
* **ip** to create network interfaces and turn them on or off
* **brctl** to manage Linux bridges
* **sysctl** to change system settings
* **qemu-img** to get virtual disk information while building Vagrant boxes

[^KVMOK]: The easiest way to meet this requirement might be to [download the **kvm-ok** source code](https://bazaar.launchpad.net/~cpu-checker-dev/cpu-checker/trunk/view/head:/kvm-ok) and make it an executable script somewhere in your PATH.

To see the Linux commands executed by various _netlab_ commands, use the `--dry-run` option of **netlab up**, **netlab down**, or **netlab connect**.

## netlab Installation

Install the Python package with `sudo python3 -m pip install networklab` or your preferred Python package installation procedure.

```{tip}
Installing Python packages as root is not recommended. If you're not setting up a throwaway VM/server, please use your regular Python package installation process.
```

## Creating *vagrant-libvirt* Virtual Network

*vagrant-libvirt* plugin connects management interfaces of managed VMs to *vagrant-libvirt* virtual network. Vagrant can determine the device IP address based on dynamic DHCP mappings; *netlab* can't. To make the Ansible inventory created by **[netlab create](../netlab/create.md)** work, your virtual network MUST include static DHCP bindings that map management MAC addresses defined in the *netlab* data model into expected IP addresses.

**[netlab up](../netlab/up.md)** command automatically creates *vagrant-libvirt* virtual network with correct static DHCP bindings before calling **vagrant up**, so you SHOULD use **netlab up** instead of executing **vagrant** commands. Recent versions of the *vagrant-libvirt* plugin remove the *vagrant-libvirt* virtual network on **vagrant destroy**, so it makes no sense to create that network manually.

(install-linux-server-test)=
## Testing the Installation

The easiest way to test your installation is to use the **[netlab test](../netlab/test.md)** command. If you prefer to do step-by-step tests, you might find this recipe helpful:

* Create an empty directory and `topology.yml` file with the following contents within that directory:

```
---
defaults:
  device: frr

module: [ ospf ]

nodes: [ s1, s2, s3 ]
links: [ s1-s2, s2-s3, s1-s2-s3 ]
```

* Start the lab with `netlab up`
* Connect to the FRR devices with the `netlab connect` command
* Destroy the lab with `netlab down`

## Host Networking Caveats

*netlab* relies on standard Linux bridges to implement multi-access links. If you encounter a situation where Layer-2 traffic passes through the bridge but there's no Layer-3 connectivity,  you're probably fighting with a too-aggressive firewall.

The easiest way to work around that problem is to turn off your distribution's firewall and reboot. In NixOS, the operating system where this problem was first encountered, you can follow this recipe:

* Open your global `configuration.nix` file in the editor of your choice
* Add the configuration option `networking.firewall.enable  = false;` Save the file
* Execute `nixos-rebuild switch` command to reach the new desired configuration state
* Reboot into the new configuration


```eval_rst
.. toctree::
   :caption: Next Steps
   :maxdepth: 1
   :titlesonly:

   ../labs/libvirt.md
   ../labs/clab.md
```
