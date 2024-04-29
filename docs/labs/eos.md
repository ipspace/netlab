# Building an Arista EOS Vagrant Libvirt Box

Arista EOS is supported by the **netlab libvirt package** command. To build an Arista EOS box:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download vEOS disk image (.qcow2 file) into that directory (Arista no longer provides downloadable Vagrant boxes).

```{tip}
Use the `eos-downloader` Python package to simplify vEOS image download. See the [eos-downloader documentation](https://pypi.org/project/eos-downloader/) for more details.
```

* Execute **netlab libvirt package eos _virtual-disk-file-name_** and follow the instructions

```{warning}
If you're using a *‌netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

## Initial Device Configuration

During the box-building process (inspired by the [step-by-step instructions by Brad Searle](https://codingpackets.com/blog/arista-veos-vagrant-libvirt-box-install/)) you'll have to copy-paste initial device configuration. **netlab libvirt config eos** command displays the build recipe:

```{eval-rst}
.. include:: eos.txt
   :literal:
```
