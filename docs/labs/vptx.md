# Building a Juniper vPTX (vJunos EVO) Libvirt Box

Juniper vPTX (known as `vJunos EVO` or `vJunos Evolved`) is supported by the **netlab libvirt package** command. To build it:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download the `Juniper vPTX` QCOW image from [here](https://support.juniper.net/support/downloads/?p=vjunos-evolved), and place into that directory
* Execute **netlab libvirt package vptx _virtual-disk-file-name_** and follow the instructions

```{warning}
* *netlab* release 1.7.0 supports only vJunosEvolved releases that do not require external PFE- and RPIO links. The first vJunosEvolved release implementing internal PFE- and RPIO links is the release 23.2R1-S1.8.
* The **‌netlab libvirt package vptx** command has been tested on Ubuntu 20.04 LTS and 22.04 LTS and might not work on other Linux distros.
* On Ubuntu 22.04 LTS, `libvirt-qemu` user needs read- and execute access to the VM disk file. It's easiest to create Vagrant boxes in a subdirectory of the `/tmp` directory.
* Juniper vJunos EVO uses Linux instead of BSD as the underlying OS. The management interface name became `re0:mgmt-0`.
```

## Initial Device Configuration

Initial device configuration is copied from a disk image created by the installation process. You'll have to save it and shut down the VM. **netlab libvirt config vptx** command displays the build recipe:

```{eval-rst}
.. include:: vptx.txt
   :literal:
```
