(build-vsrx)=
# Building a Juniper vSRX 3.0

Juniper vSRX 3.0 is supported by the **netlab libvirt package** command. To build a vSRX 3.0 box:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download vSRX 3.0 disk image (.qcow2 file) into that directory
* Execute **netlab libvirt package vsrx _virtual-disk-file-name_** and follow the instructions

```{warning}
_netlab_ uses `pc-i440fx-6.2` QEMU machine type to run vSRX VMs due to vSRX [PR 1819545](https://prsearch.juniper.net/PR1819545) ([public information](https://supportportal.juniper.net/s/article/22-4R3-S4-SRN)) that has been fixed in vSRX release 24.2R1.

We tested the Vagrant box on Ubuntu 22.04 and 24.04. If the vSRX Vagrant box doesn't build or doesn't work on your Linux distribution, please try out the vSRX [*‌vrnetlab* container](clab-vrnetlab).
```

## Preparing the Box Configuration

The initial device configuration is copied from an ISO image created by the installation process. You'll have to save it and shut down the VM. **netlab libvirt config vsrx** command displays the build recipe (based on the [recipe published by Brad Searle](https://codingpackets.com/blog/juniper-vsrx3-0-vagrant-libvirt-box-install/)):

```{eval-rst}
.. include:: vsrx.txt
   :literal:
```

## Notes on Using vSRX Box

The *netlab* Vagrant template for vSRX uses *default\_prefix* libvirt parameter to set the domain (VM) name and uses the VM name to set the libvirt vCPU quota.

The template has been tested with Vagrant version 2.2.14. Some earlier versions of Vagrant generated VM names using a slightly different algorithm (the underscore between _default\_prefix_ and VM name was added automatically) and might thus generate an unexpected VM name. To fix that problem, remove parts of **vsrx-domain.j2** template:

* Remove _domain.default\_prefix_ parameter (default value should generate the expected VM name) or
* Remove the whole CPU-limiting logic (trading CPU cycles for simplicity)
