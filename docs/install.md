# Installation

*netlab* is a Python3 package[^NSL] that uses Python 3.8[^P38] or later. We recommend using _netlab_ on Linux (we're doing all our tests on Ubuntu), including Windows Subsystem for Linux or [Multipass on macOS](https://blog.ipspace.net/2024/03/netlab-bgp-apple-silicon/). While you might be able to get _netlab_ to run natively on Windows or macOS with VirtualBox, we no longer support that.

[^P38]: We keep supporting Python 3.8 because it's the default Python distribution on Ubuntu 20.04.

[^NSL]: For legacy reasons, the *netlab* Python code resides in *netsim.\** modules.

_netlab_ is a high-level abstraction and orchestration tool that relies on other tools to provide the low-level functionality:

* VM/container virtualization with KVM or Docker[^NVB]
* Virtualization API: libvirt (used with KVM on Linux)
* VM/container orchestration: Vagrant or containerlab
* Configuration deployment: Ansible 2.9.1[^ANS] or later

[^NVB]: VirtualBox virtualization provider is still available, but no longer developed or supported.

[^ANS]: Ansible 2.9 has been tested with Arista EOS, Cisco IOS/IOL/IOS-XE, Cisco NX-OS, Junos, Cumulus Linux, FRR, generic Linux devices, and VyOS. Our [integration tests](https://release.netlab.tools/) use recent Ansible versions. Some devices might require additional Ansible collections; see [caveats](caveats.md) for further details.

![High-level architecture](high-level-architecture.png)

If you already have an environment that can be used with *netlab*, please proceed directly to *[installing Python package](package)*. Otherwise, you'll have to [select the platform](platform) you want to use and [create your lab environment ](lab)(including *netlab* installation). You can also run _netlab_ with container-based network devices in GitHub Codespaces ([netlab examples](https://blog.ipspace.net/2024/07/netlab-examples-codespaces/), [BGP labs](https://bgplabs.net/4-codespaces/), [IS-IS labs](https://isis.bgplabs.net/4-codespaces/)).

(platform)=
## Selecting the Platform and Low-Level Tools

We have tested *netlab* with [libvirt/KVM and Vagrant](labs/libvirt.md) on Ubuntu and Fedora and with [Docker and containerlab](labs/clab.md) on Ubuntu[^VBH]. Both combinations should work on other Linux distributions. You can also run *netlab* in a [Linux virtual machine](install/ubuntu-vm.md) or a [Ubuntu instance in a public cloud](install/cloud.md).

[^VBH]: Historically, netlab also ran on [VirtualBox and Vagrant](labs/virtualbox.md) on macOS with Intel silicon. That combination is no longer supported.

When selecting the virtualization environment, consider the following:

* We are developing and testing _netlab_ on Ubuntu. Ubuntu-based _netlab_ is also easiest to set up; the **[netlab install](netlab-install)** command does all the heavy lifting for you and installs all the prerequisite software (KVM, libvirt, Vagrant, Docker, containerlab, Ansible).
* **Vagrant provider for libvirt** supports parallel VM provisioning, resulting in pretty fast lab creation. Unfortunately, most vendors don't offer virtual devices packaged as libvirt Vagrant boxes, so you must build your boxes manually. The **[netlab libvirt package](netlab-libvirt-package)** usually does 90% of the work for you.
* **Containers** provisioned with containerlab start much faster than virtual machines, but you can get only a few network devices in native container format (Arista cEOS, FRR, Nokia SR Linux, VyOS). On the other hand, the [**vrnetlab** fork by Roman Dodin](https://github.com/srl-labs/vrnetlab) can build containers running virtual machines for numerous network devices.

We no longer recommend or support **VirtualBox**-based solutions. It is no longer needed on Windows; Windows Subsystem for Linux is a much better option. Apple stopped shipping x86-based hardware years ago, and no major vendor is shipping ARM-based VM images for network devices.

(lab)=
## Creating the Lab Environment

We have documented how you can set up your lab:

* On a [Ubuntu virtual machine running on Windows or MacOS](install/ubuntu-vm.md).
* On a [generic Ubuntu VM or bare-metal Ubuntu server](install/ubuntu.md)
* On [other Linux distributions](install/linux.md)
* In a [public cloud](install/cloud.md)

```{tip}
If you decide to run the network labs within an Ubuntu VM, [create a new VM and use the automated software installation procedure](install/ubuntu-vm.md). Starting with a fresh VM is much easier and safer than installing the necessary software on an existing VM.
```

Finally, you can use _netlab_ on Apple Silicon ([basics](https://blog.ipspace.net/2024/03/netlab-bgp-apple-silicon/), [using Arista cEOS](https://blog.ipspace.net/2025/02/arista-ceos-arm-apple-silicon/)), but all we managed to do was to run containers (Arista EOS, FRR, SR Linux) on a Multipass-provisioned Ubuntu VM. If you're using a laptop with Apple silicon, run more complex labs on a [Ubuntu VM](ubuntu-vm-manual) running on-premises or in a [public cloud](install/cloud.md), or a [bare-metal server](install/ubuntu.md).

## Building Boxes and Containers

* You might have to build Vagrant boxes for your network devices if you use [*libvirt* with KVM on a Linux system](labs/libvirt.md). *netlab* includes [box building recipes](libvirt-vagrant-boxes) for most supported platforms.
* You can get a [few network devices as Docker containers](labs/clab.md#container-images) you can use with [*containerlab*](labs/clab.md). You can also build Docker containers from VM images with **[vrnetlab](https://github.com/srl-labs/vrnetlab)**.

(package)=
## Installing Python Package

To install *netlab* on an existing system that already has the low-level tools installed, use `python3 -m pip install networklab`. The installation process will install all prerequisite Python packages and create the **netlab** command.

If you want to get the latest development code or if you want to participate in *netlab* development, [clone the GitHub repository](install/clone.md).

```eval_rst
.. toctree::
   :caption: Next Steps
   :maxdepth: 1
   :hidden:

   install/ubuntu-vm.md
   install/ubuntu.md
   install/linux.md
   install/cloud.md
   labs/libvirt.md
   labs/clab.md
   install/clone.md
```
```eval_rst
.. toctree::
   :caption: Deprecated
   :maxdepth: 1
   :hidden:

   labs/virtualbox.md
```