(install-linux-server)=
# Running *netlab* on a Linux Server

This page describes generic installation steps for creating a virtual lab environment on any Linux distribution ([follow these instructions](ubuntu.md) if you plan to run your labs on a Debian or Ubuntu server, including Windows Subsystem for Linux).

```{warning}
We test _netlab_ on Ubuntu to provide a reasonably hassle-free experience for networking engineers without Linux sysadmin skills. Unfortunately, we cannot help you if you run _netlab_ on another Linux distribution (dealing with one distro is more than enough pain). Still, please try to make it work; we would appreciate it if you could add your findings to this document. Thank you!
```

## Prerequisite Software Installation

*netlab* is a Python package that uses Docker or Podman to run containers and libvirt with KVM to run virtual machines. Virtual machines in the KVM environment and the associated Linux bridges are created with Vagrant using the libvirt API. *netlab* uses shell scripts, Netmiko, or Ansible to configure network devices.

![netlab on Linux](linux-architecture.png)

To build a Linux environment needed to run network devices as virtual machines or containers:

* Install Python 3.10 or later (use the latest Python version supported by your Linux distribution)

If you want to run network devices as virtual machines with KVM:

* Install KVM and libvirt
* Install Vagrant 2.4.9 or later[^CSV]
* Install *vagrant-libvirt* plugin with `vagrant plugin install libvirt --plugin-version=0.12.2`

If you want to run network devices as containers (or virtual machines in *vrnetlab* containers), install Docker and containerlab.

```{tip}
If possible, [use containerlab](lab-clab) and package the virtual machines you need in [_vrnetlab_ containers](clab-vrnetlab). Getting Vagrant to work on some Linux distributions can be a bit challenging.
```

[^CSV]: Please check the [libvirt installation script](https://github.com/ipspace/netlab/blob/dev/netsim/install/libvirt.sh) for the recommended Vagrant release.

Finally, install Ansible 2.9.1 or later and any Ansible networking dependencies (example: paramiko). We recommend using the latest Ansible 11.x release. You _might_ be able to use the **netlab install ansible** command (after [installing netlab](install-linux-netlab)) instead of manual installation.

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

(install-linux-netlab)=
## netlab Installation

Install the Python package with `sudo python3 -m pip install networklab` or your preferred Python package installation procedure.

```{tip}
Installing Python packages as root is not recommended. If you're not setting up a throwaway VM/server, please use your regular Python package installation process.
```

## Creating *vagrant-libvirt* Virtual Network

Always start your labs with the **[netlab up](netlab-up)** command; it automatically creates the *vagrant-libvirt* virtual network with correct static DHCP bindings before calling **vagrant up**. Recent versions of the *vagrant-libvirt* plugin remove the *vagrant-libvirt* virtual network on **vagrant destroy** (called by **netlab down**); creating that network manually makes no sense.

(install-linux-server-test)=
## Testing the Installation

The easiest way to test your installation is to use the **[netlab test](../netlab/test.md)** command. If you prefer to do step-by-step tests, you might find this recipe helpful:

* Create an empty directory and a `topology.yml` file with the following contents within that directory:

```
---
defaults:
  device: frr

module: [ ospf ]

nodes: [ s1, s2, s3 ]
links: [ s1-s2, s2-s3, s1-s2-s3 ]
```

* Start the lab with `netlab up` to test *libvirt* installation or `netlab up -p clab` to test *containerlab* installation
* Connect to the FRR devices with the `netlab connect` command
* Destroy the lab with `netlab down`

## Host Networking Caveats

*netlab* relies on standard Linux bridges to implement multi-access links. If you encounter a situation where Layer-2 traffic passes through the bridge but there's no Layer-3 connectivity,  you're probably fighting with a too-aggressive firewall.

The easiest workaround is to turn off your distribution's firewall and reboot. In NixOS, the operating system where this problem was first encountered, you can follow this recipe:

* Open your global `configuration.nix` file in the editor of your choice
* Add the configuration option `networking.firewall.enable  = false;` Save the file
* Execute `nixos-rebuild switch` command to reach the new desired configuration state
* Reboot into the new configuration

## Next Steps

* [](lab-clab)
* [](lab-libvirt)
