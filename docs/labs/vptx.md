# Building a Juniper vPTX (vJunos EVO) Libvirt Box

Juniper vPTX (known as `vJunos EVO` or `vJunos Evolved`) is supported by the **netlab libvirt package** command. To build it:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download the `Juniper vPTX` QCOW image from [here](https://support.juniper.net/support/downloads/?p=vjunos-evolved), and place into that directory
* Execute **netlab libvirt package vptx _virtual-disk-file-name_** and follow the instructions

```{warning}
* Use *netlab* release 1.7.0 or higher with Juniper vPTX devices.
* Juniper vJunos EVO uses Linux instead of BSD as the underlying OS. The management interface name became `re0:mgmt-0`.
* If you're using a *‌netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

## Initial Device Configuration

Initial device configuration is copied from a disk image created by the installation process. You'll have to save it and shut down the VM. **netlab libvirt config vptx** command displays the build recipe:

```{eval-rst}
.. include:: vptx.txt
   :literal:
```
