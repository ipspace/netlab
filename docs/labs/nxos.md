(build-nxos)=
# Cisco Nexus 9300v Vagrant Libvirt Boxes

Cisco Nexus 9300v is supported by the **netlab libvirt package** command. To build a Nexus 9300v box:

* Create an empty directory on an Ubuntu machine with *libvirt* and *Vagrant*.
* Download Nexus 9300v disk image (.qcow2 file) into that directory
* Execute **netlab libvirt package nxos _virtual-disk-file-name_** and follow the instructions

```{warning}
* The box-building process generates a random device serial number that will be used by all Nexus 9300v devices created from the Vagrant box. As NX-OS uses the device serial number as its DHCP client ID, you might experience problems starting a lab with more than one Nexus 9300v device on newer versions of KVM/libvirt. The workaround-of-last-resort is [setting libvirt **batch_size** to 1](libvirt.md#starting-virtual-machines-in-batches).
* If you're using a *‌netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

```{tip}
See [Cisco Nexus OS Caveats](caveats-nxos) if you want to run NX OS 10.1 or later
```

## Initial Device Configuration

During the box-building process (inspired by [this solution](https://github.com/mweisel/cisco-nxos9kv-vagrant-libvirt)) you'll have to copy-paste the initial device configuration. **netlab libvirt config nxos** command displays the build recipe:

```{eval-rst}
.. include:: nxos.txt
   :literal:
```
