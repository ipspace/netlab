# Building an Arista EOS Vagrant Libvirt Box

Arista EOS is supported by the **netlab libvirt package** command. To build an Arista EOS box:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download vEOS disk image (.qcow2 file) into that directory (Arista no longer provides downloadable Vagrant boxes).

```{tip}
Use the `eos-downloader` Python package to simplify vEOS image download. See the [eos-downloader documentation](https://pypi.org/project/eos-downloader/) for more details.
```

* Execute **netlab libvirt package eos _virtual-disk-file-name_** and follow the instructions

## Initial Device Configuration

During the box-building process (inspired by the [step-by-step instructions by Brad Searle](https://codingpackets.com/blog/arista-veos-vagrant-libvirt-box-install/)) you'll have to copy-paste initial device configuration. **netlab libvirt config eos** command displays the build recipe:

```{eval-rst}
.. include:: eos.txt
   :literal:
```

```{warning}
* The **‌netlab libvirt package eos** command has been tested on Ubuntu 20.04 LTS and 22.04 LTS and might not work on other Linux distros.
* On Ubuntu 22.04 LTS, `libvirt-qemu` user needs read and execute access to the VM disk file. It's easiest if you create Vagrant boxes in a subdirectory of the `/tmp` directory.
```
