# Building a Juniper vSRX 3.0

Juniper vSRX 3.0 is supported by the **netlab libvirt package** command. To build a vSRX 3.0 box:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download vSRX 3.0 disk image (.qcow2 file) into that directory
* Execute **netlab libvirt package vsrx _virtual-disk-file-name_** and follow the instructions

```{warning}
If you're using a *‌netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

## Preparing the Box Configuration

Initial device configuration is copied from an ISO image created by the installation process. You'll have to save it and shut down the VM. **netlab libvirt config vsrx** command displays the build recipe (based on the [recipe published by Brad Searle](https://codingpackets.com/blog/juniper-vsrx3-0-vagrant-libvirt-box-install/)):

```{eval-rst}
.. include:: vsrx.txt
   :literal:
```

## Notes on Using vSRX Box

The *netlab* Vagrant template for vSRX uses *default\_prefix* libvirt parameter to set the domain (VM) name and uses the VM name to set libvirt vCPU quota.

The template has been tested with Vagrant version 2.2.14. Some earlier versions of Vagrant generated VM names using a slightly different algorithm (the underscore between _default\_prefix_ and VM name was added automatically) and might thus generate an unexpected VM name. To fix that problem remove parts of **vsrx-domain.j2** template:

* Remove _domain.default\_prefix_ parameter (default value should generate the expected VM name) or
* Remove the whole CPU-limiting logic (trading CPU cycles for simplicity)
