(lab-virtualbox)=
# VirtualBox-Based Lab on Windows or MacOS

VirtualBox-based Vagrant lab was an interesting option to run *netlab* directly on Windows or macOS on x86 hardware. The world has moved on; Microsoft launched Windows Subsystem for Linux, and Apple started shipping ARM-based hardware (that's when we stopped developing new VirtualBox features). 

Instead of VirtualBox, use Windows Subsystem for Linux, Multipass-provisioned Ubuntu VM on macOS (you'll be limited to a few ARM-based containers), or an external Ubuntu server or VM.

```{warning}
* The **‌virtualbox** provider will be removed in a future _netlab_ release. Do not use it for new installations.
* We no longer have the infrastructure to test the **‌virtualbox** provider and cannot guarantee that it still works.
* VirtualBox on macOS cannot run x86 VMs on Apple silicon, making it useless in an environment where most vendors ship only x86-based VM images.
```

When running _netlab_ with `virtualbox` provider:

* [netlab](../netlab/cli.md) commands create Ansible inventory and Vagrant configuration.
* Vagrant creates virtual networks within the VirtualBox environment and starts network devices as virtual machines within VirtualBox.
* Ansible connects to the network devices using SSH ports mapped by Virtualbox and configures them.

![VirtualBox-based architecture](../install/virtual-box-architecture.png)

The VirtualBox environment is pretty easy to set up:

* [Install Virtualbox](https://www.virtualbox.org/wiki/Downloads) (might require fiddling with BIOS setup)
* [Install Vagrant](https://www.vagrantup.com/docs/installation)
* Assuming you already have Python3 installed, install *netlab* Python package with `pip3 install networklab`
* [Install Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)[^1] and related device-specific requirements (see Ansible documentation for details).
* Test the installation with **[netlab test virtualbox](../netlab/test.md)** command

## Creating a New Lab
To create a new lab:

* Create [lab topology file](../topology-overview.md) in an empty directory. Use `provider: virtualbox` in the lab topology to select the *virtualbox* virtualization provider.
* Execute **[netlab up](../netlab/up.md)**

[^1]: Running Ansible on Windows is not supported, but supposedly it runs just fine under WSL. 

## Testing the Installation

The easiest way to test your installation is to use the **netlab test** command. If you prefer to do step-by-step tests, or if you don't want to install Ansible, use this recipe:

* Create an empty directory and `topology.yml` file with the following contents within that directory:

```
---
defaults:
  device: cumulus

nodes: [ s1, s2, s3 ]
links: [ s1-s2, s2-s3, s1-s2-s3 ]
```

* Execute `netlab up --no-config` to create configuration files and start the lab without configuring network devices (that step would require Ansible)
* Connect to the Cumulus VX devices with `vagrant ssh`
* Destroy the lab with `netlab down`

## Creating Vagrant Boxes

Vagrant relies on *boxes* (prepackaged VM images). The following Vagrant boxes are automatically downloaded from Vagrant Cloud when you're using them for the first time in your lab topology:

| Virtual network device | Vagrant box name   |
|------------------------|--------------------|
| Cumulus VX             | CumulusCommunity/cumulus-vx:4.4.0 |
| Cumulus VX 5.0 (NVUE)            | CumulusCommunity/cumulus-vx:5.0.1|
| Generic Linux          | generic/ubuntu2004 |

You must download Arista vEOS and Nexus 9300v images from the vendor website (requires registration) and install them with the **vagrant box add _filename_ \-\-name _boxname_** command. You'll find build recipes for other network devices on [codingpackets.com](https://codingpackets.com/blog/tag/#vagrant).

You have to use the following box names when installing or building the Vagrant boxes:

| Virtual network device | Vagrant box name   |
|------------------------|--------------------|
| Arista vEOS            | arista/veos        |
| Cisco IOSv             | cisco/iosv         |
| Cisco CSR 1000v        | cisco/csr1000v     |
| Cisco Nexus 9300v      | cisco/nexus9300v   |
| Juniper vSRX 3.0       | juniper/vsrx3      |

**Notes**:

* Arista rarely ships the latest software version as a Vagrant box. You'll usually have to build a Vagrant box to have an up-to-date EOS version.
* Vagrantfile created by **netlab create** or **netlab up** sets up port forwarding for SSH (22), HTTP (80), and NETCONF (830), but the corresponding Ansible inventory contains only **ansible_port** (SSH). You could edit the final inventory by hand, add an extra file to `host_vars`, or fix the *netlab* code. Should you decide to do the latter, please get in touch with us in advance to discuss the necessary data structures.
* If you want to add other network devices, build your own Vagrant boxes and modify the system *topology-defaults.yml* file or [user defaults](defaults-user-file) (see [_adding new virtualization provider for an existing device_](../dev/device-platform.md) for more details). 
