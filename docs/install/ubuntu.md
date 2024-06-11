# Ubuntu Server Installation

On a Linux system, *netlab* uses KVM to run virtual machines and Docker to run containers. Virtual machines in KVM environment and the associated Linux bridges are created with Vagrant using libvirt API. Ansible is used to configure the network devices.

![netlab-tools on Linux](linux-architecture.png)

The simplest way to install *netlab* and the whole low-level toolchain on an existing Ubuntu server (bare-metal or VM) is to use the **[netlab install](../netlab/install.md)** command (see below). You could also [do manual software installation](linux.md).

* If needed, install Python3 and **pip3** with `sudo apt-get update && sudo apt-get install -y python3-pip`
* Install Python package with `sudo python3 -m pip install networklab` or your preferred Python package installation procedure.

```{tip}
* Installing Python packages as root is not the recommended best practice (but gets around the potential PATH problems). Please use your regular Python package installation process if you're not setting up a throwaway VM/server.
* Ubuntu 22.04 wants you to install Python packages in a virtual environment. If you're working on a throwaway VM/server, stop **‌pip** complaints with the `--break-system-packages` option.
```

* Install additional software with `netlab install ubuntu ansible libvirt containerlab` command ([more details](../netlab/install.md)).

```eval_rst
.. toctree::
   :caption: Next Steps
   :maxdepth: 1
   :titlesonly:

   ../labs/libvirt.md
   ../labs/clab.md
```
