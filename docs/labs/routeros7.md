(build-chr7)=
# Building a Mikrotik RouterOS 7 CHR Libvirt Box

Mikrotik RouterOS 7 CHR is supported by the **netlab libvirt package** command. To build it:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download the CHR 7 vmdk disk image into that directory (unzip the ZIP archive if you downloaded a .zip file)
* Execute **netlab libvirt package routeros7 _virtual-disk-file-name_** and follow the instructions

```{warning}
If you're using a *‌netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

## Initial Device Configuration

During the box-building process (inspired by the [step-by-step instructions by Stefano Sasso](http://stefano.dscnet.org/a/mikrotik_vagrant/)), you'll have to copy-paste the initial device configuration. **netlab libvirt config routeros7** command displays the build recipe:

```{eval-rst}
.. include:: routeros7.txt
   :literal:
```

## Hack for the ether1 Interface

The initial device configuration includes a hack to create a DHCP address on the new VM's first ethernet interface (*ether1*).

*RouterOS* saves the existing network interfaces, together with their names, and checks for their existence on subsequent boots. Every time it finds a new ethernet interface, the new interface is added to the list with a "sequence number," i.e., ether2, ether3, and so on.

The network interface we used during the installation will no longer be present at the next boot time, and the "new" first interface will be called *ether2*, which we don’t like.

However, if we rename the current interface to something other than *ether1*, the "new" first interface will be called *ether1* -- exactly what we need.

At the same time, since the DHCP client configuration is linked to the current interface (and the configuration is referenced by ID, not by interface name), we need to change the DHCP Client configuration on every boot to use the new *ether1* interface -- that's the role of the system scheduler script included in the initial configuration.
