# Building an Mikrotik RouterOS 7 CHR Libvirt Box

Mikrotik RouterOS 7 CHR is supported by the **netlab libvirt package** command. To build it:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download the CHR 7 vmdk disk image into that directory
* Convert the image to the *qcow2* format (`qemu-img convert -f vmdk -O qcow2 chr-7.5.vmdk chr-7.5.qcow2`)
* Execute **netlab libvirt package routeros7 _virtual-disk-file-name_** and follow the instructions

```{warning}
* The **‌netlab libvirt package routeros7** command has been tested on Ubuntu 20.04 LTS and might not work on other Linux distros.
* On Ubuntu 22.04 LTS, `libvirt-qemu` user needs read and execute access to the VM disk file. It's easiest if you create Vagrant boxes in a subdirectory of the `/tmp` directory.
```

## Initial Device Configuration

During the box-building process (inspired by the [step-by-step instructions by Stefano Sasso](http://stefano.dscnet.org/a/mikrotik_vagrant/)) you'll have to copy-paste initial device configuration. **netlab libvirt config routeros7** command displays the build recipe:

```{eval-rst}
.. include:: routeros7.txt
   :literal:
```

## Hack for ether1 interface

The initial device configuration includes an hack for having a DHCP address on the first ethernet interface of the new VM (*ether1*).

*RouterOS* saves somewhere the existing network interfaces, together with their own names, checking for their existance on the subsequent boots. Every time it founds a new ethernet interface, this will be added to the list with a "sequence number", i.e., ether2, ether3, and so on.

The network interface we are using during the installation won't be present anymore on the next boot time, and the "new" first interface will be called *ether2* - which we don’t like.

But, we can simply rename the current interface to something different than *ether1*. Doing so, the "new" first interface will be called exactly *ether1*. Much better!

At the same time, since any configuration about DHCP Client is linked to the current interface (and the configuration is referenced by ID, not by interface name), we need to change the DHCP Client config on every boot to use the new *ether1* interface. This can be done using a system scheduler script at every system startup.
