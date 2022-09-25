# Building a Cisco CSR 1000v Vagrant Libvirt Box

Cisco CSR 1000v is supported by the **netlab libvirt package** command. To build a CSR 1000v box:

* Create an empty directory on a Ubuntu machine with *libvirt* and *Vagrant*.
* Download a CSR disk image (.qcow2 file) with -serial in the file name (example: `csr1000v-universalk9.17.03.04a-serial.qcow2`) into that directory
* Execute **netlab libvirt package csr _virtual-disk-file-name_** and follow the instructions

```{warning}
* You MUST have a CSR disk image that expects to be configured through the serial interface for this procedure to work. If all you have is an image that expects a graphics card, the [original recipe on codingpackets.com](https://codingpackets.com/blog/cisco-iosv-vagrant-libvirt-box-install/) might still work for you.
* The **‌netlab libvirt package csr** command has been tested on Ubuntu 20.04 LTS and 22.04 LTS and might not work on other Linux distros.
* On Ubuntu 22.04 LTS, `libvirt-qemu` user needs read and execute access to the VM disk file. It's easiest if you create Vagrant boxes in a subdirectory of the `/tmp` directory.
```

## Initial Device Configuration

During the box-building process (inspired by [this solution](https://github.com/mweisel/cisco-nxos9kv-vagrant-libvirt)) you'll have to copy-paste initial device configuration. **netlab libvirt config csr** command displays the build recipe (based on the [recipe published by Brad Searle](https://codingpackets.com/blog/cisco-csr-1000v-vagrant-libvirt-box-install/)):

```{eval-rst}
.. include:: csr.txt
   :literal:
```

## Notes on Using CSR Box

If you're experiencing high CPU utilization with Cisco CSR, [set halt_poll_ns to zero](https://codingpackets.com/blog/kvm-host-high-cpu-fix/).
