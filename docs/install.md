# Installation

*netsim-tools* is a Python3 package that runs on Python 3.7 or later on Windows, MacOS, or Linux. It's a high-level abstraction and orchestration tool that relies on other tools to provide the low-level functionality:

* VM/container virtualization: VirtualBox, libvirt/KVM or Docker
* VM/container orchestration: Vagrant or containerlab
* Configuration deployment: Ansible 2.9.1 or later

## Selecting the Platform and Low-Level Tools

We have tested *netsim-tools* with:

* VirtualBox and Vagrant on MacOS. The same combination should also work on Windows 10. Ansible works on MacOS; RedHat claims it works (but is not supported) within Windows Subsystem for Linux (WSL).
* libvirt/KVM and Vagrant on Ubuntu and Fedora. This combination should work on other Linux distributions.
* Docker and containerlab on Ubuntu. This combination should also work on other Linux distributions.

When selecting the virtualization environment, consider the following:

**VirtualBox** is commonly used together with Vagrant as a laptop virtualization solution, resulting in wider variety of prepackaged boxes (Arista vEOS, Cisco Nexus 9300v, Cumulus VX, Juniper vSRX). The downsides: 

* Slow lab setup due to serial provisioning;
* No management network (Vagrant uses a weird port NAT to access virtual machines)
* VirtualBox networking is hard to integrate with the external world

**Vagrant provider for libvirt** supports parallel VM provisioning, resulting in much faster lab creation. Unfortunately, most vendors don't offer virtual devices packaged as libvirt Vagrant boxes, so you'll have to build your own boxes.

**Containers** provisioned with containerlab start much faster than virtual machines, but you can get only a few network devices in native container format (Arista cEOS, Nokia SR Linux, Cumulus VX).

We are focusing the majority of our platform development efforts on Linux environments using KVM/libvirt with Vagrant or Docker with containerlab. We have selected Ubuntu as the distribution supported by **netlab install** command. The *libvirt* installation guide for Ubuntu is thus the most extensive one.

## Creating the Lab Environment

You can set up your lab:

* On [Windows or MacOS using VirtualBox with Vagrant](labs/virtualbox.md). This setup won't be able to run network devices packaged as containers (Arista cEOS, Nokia SR Linux)
* On a [Ubuntu virtual machine running on Windows or MacOS](install/ubuntu-vm.md).
* On a [Ubuntu VM or bare-metal Ubuntu server](install/ubuntu.md)
* On [other Linux distributions](install/linux.md)

```{tip}
We highly recommend to use KVM+libvirt on Linux, and see no good reason to use VirtualBox when there are better alternatives.
```

## Installing *netsim-tools* Package

To install *netsim-tools* on a system that already has the low-level tools installed, use `python3 -m pip install netsim-tools`. The installation process will install all prerequisite Python packages and create the **netlab** command.

If you want to get the latest development code or if you want to participate in *netsim-tools* development, [clone the GitHub repository](install/clone.md).

```eval_rst
.. toctree::
   :caption: Next Steps
   :maxdepth: 1
   :hidden:

   labs/virtualbox.md
   install/ubuntu-vm.md
   install/ubuntu.md
   install/linux.md
   labs/libvirt.md
   labs/clab.md
   install/clone.md
```
