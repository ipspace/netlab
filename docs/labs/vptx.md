# Building a Juniper vPTX (vJunos EVO) Libvirt Box

Juniper vPTX (known as `vJunos EVO` or `vJunos Evolved`) is supported by the **netlab libvirt package** command. To build it:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download the `Juniper vPTX` QCOW image from [here](https://support.juniper.net/support/downloads/?p=vjunos-evolved), and place into that directory
* Execute **netlab libvirt package vptx _virtual-disk-file-name_** and follow the instructions

```{warning}
* The **‌netlab libvirt package vptx** command has been tested on Ubuntu 20.04 LTS and 22.04 LTS and might not work on other Linux distros.
* On Ubuntu 22.04 LTS, `libvirt-qemu` user needs read and execute access to the VM disk file. It's easiest if you create Vagrant boxes in a subdirectory of the `/tmp` directory.
* Juniper vJunos EVO uses Linux instead of BSD as base OS. There are some basic differences from a "default" JunOS instance, including the management interface name, which becames "re0:mgmt-0".
* The management interface DHCP client might not work correctly on vJunosEvolved release 23.2R1.15. If you're experiencing problems, use release 23.1R1.8.
```

## Initial Device Configuration

Initial device configuration is copied from a disk image created by the installation process. You'll have to save it and shut down the VM. **netlab libvirt config vptx** command displays the build recipe:

```{eval-rst}
.. include:: vptx.txt
   :literal:
```
