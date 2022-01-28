# Building an Arista EOS Vagrant Libvirt Box

Arista EOS is supported by the **netlab libvirt package** command. To build an Arista EOS box:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download vEOS disk image (.vmdk or .qcow2 file) into that directory
* Execute **netlab libvirt package eos _virtual-disk-file-name_** and follow the instructions

## Initial Device Configuration

During the box-building process (inspired by the [step-by-step instructions by Brad Searle](https://codingpackets.com/blog/arista-veos-vagrant-libvirt-box-install/)) you'll have to copy-paste initial device configuration. **netlab libvirt config eos** command displays the build recipe:

```{eval-rst}
.. include:: eos.txt
   :literal:
```

## Mutating Virtualbox Boxes

Some releases of Arista vEOS are available as Virtualbox boxes. To use them with *vagrant-libvirt*:

* Install Vagrant *mutate* plugin with **vagrant plugin install vagrant-mutate**
* Download the box file from vendor web site
* Install *virtualbox* version of the box file with **vagrant box add *filename* \-\-name _boxname_**
* Transform *virtualbox* box into *libvirt* box with **vagrant mutate _boxname_ libvirt**
* Remove the _virtualbox_ box with **vagrant box remove _boxname_ \-\-provider virtualbox** command.

```{warning}
You might experience weird Vagrant errors when starting mutated vEOS boxes with **‌vagrant up** or **‌netlab up** command. Building a box yourself usually solves that problem.
```
 
## Notes on Arista EOS Box Building

If you use the [recipe published by Brad Searle](https://codingpackets.com/blog/arista-veos-vagrant-libvirt-box-install/) to build Arista vEOS box, you have to modify it slightly to make it work with recent vEOS releases. After applying Brad's initial configuration (**do not** configure his event handlers), execute these commands to generate PKI key and certificate:

```
security pki key generate rsa 2048 default
security pki certificate generate self-signed default key default ↩
  param common-name Arista
```

After generating PKI certificate add these configuration commands to enable NETCONF and RESTCONF

```
management api http-commands
 no shutdown
!
management api netconf
 transport ssh default
!
management api restconf
 transport https default
  ssl profile default
  port 6040
!
management security
 ssl profile default
  certificate default key default
```

Finally, remove custom shell from *vagrant* user with...

```
no user vagrant shell
```

... and follow the rest of Brad's instructions.
