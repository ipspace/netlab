(build-vyos)=
# Building a VyOS Libvirt Box

VyOS is supported by the **netlab libvirt package** command. The public `vyos/current` Vagrant box is no longer maintained; build a local Vagrant box from a recent VyOS ISO image instead.

```{warning}
Building a VyOS Libvirt box is not a straightforward process, and this recipe is maintained on a best-effort basis. Use the VyOS containerlab image whenever possible.
```

## Download a VyOS ISO Image

You can use any recent VyOS ISO image that supports the configuration syntax used by _netlab_. The usual public choices are:

* Download the latest VyOS rolling/nightly ISO image from the [VyOS rolling release builds](https://vyos.net/get/nightly-builds/) page.
* Download a VyOS Stream ISO image from the [VyOS download](https://vyos.io/) page when you prefer a less volatile public preview build.

VyOS publishes `.minisig` files for public images. Use the verification instructions on the VyOS download page if you want to validate the ISO before installing it.

The box-building process has two stages:

* Create a base qcow2 disk image with VyOS installed from the ISO image.
* Customize that installed disk image for Vagrant and package it as a Vagrant box.

The explicit `virt-install` command in the first stage is needed because **netlab libvirt package** works with an existing virtual disk image; it does not install network operating systems from ISO images.

## Create the VyOS Disk Image

Create a temporary working directory outside your home directory, download the VyOS ISO image into that directory, and create an empty virtual disk:

```
qemu-img create -f qcow2 vyos.qcow2 10G
```

The `qemu:///system` libvirt session starts the VM as an unprivileged libvirt user. That user often cannot access files under your home directory, resulting in `Cannot access storage file ... Permission denied`. Working under `/var/tmp` (or `/tmp`) and making the ISO readable and the qcow2 disk writable avoids that problem during the first-stage installation. Remove the temporary directory after you package the Vagrant box.

Start a temporary VM from the ISO image. Replace the ISO file name in the following command with the file you downloaded. The temporary VM does not need a network interface; skipping it avoids creating an `eth0` interface during the initial installation stage.

```
virt-install --connect=qemu:///system --name=vyos-install --arch=x86_64 --cpu host --vcpus=2 --hvm \
  --osinfo linux2022 --ram=1024 --network none --graphics none \
  --disk path=vyos.qcow2,format=qcow2,bus=virtio \
  --cdrom=vyos-rolling-latest.iso --boot cdrom,hd --noreboot
```

If your *virt-install* version does not recognize `linux2022`, use `virt-install --osinfo list` to find the closest generic Linux value available on your system.

The `--noreboot` option prevents *virt-install* from restarting the VM after the installation finishes or the live system powers off.

Log into the live system as `vyos` with password `vyos`, run `install image`, and install VyOS on `/dev/vda`. When the installer asks for the default console, use the default serial console. Use `vyos` as the password for the `vyos` user.

Power off the VM after the installation completes (`poweroff` command) and remove the temporary VM definition:

```
virsh undefine vyos-install
```

## Build the Vagrant Box

After creating the installed VyOS disk image, execute **netlab libvirt package vyos _virtual-disk-file-name_** and follow the instructions:

```
netlab libvirt package vyos vyos.qcow2
```

```{warning}
If you're using a *netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

## Initial Device Configuration

During the second stage, **netlab libvirt package** customizes the installed VyOS disk image for Vagrant automatically with a NoCloud cloud-init sequence. It generates a `cidata` ISO image from the files in `netsim/install/libvirt/vyos/` and attaches it to the build VM as a CD-ROM. On first boot, cloud-init installs the first-boot script into the image and powers the VM off; there is no need to configure the VM from the console. The **netlab libvirt config vyos** command displays the build recipe:

The customizing files in `netsim/install/libvirt/vyos/` are:

* `user-data` -- the cloud-init configuration that installs the first-boot script
* `meta-data` -- the minimum NoCloud metadata

The cloud-init `user-data` writes the first-boot script to `/opt/vyatta/etc/config/scripts/vyos-preconfig-bootup.script` (see the [VyOS cloud-init documentation](https://docs.vyos.io/en/latest/automation/cloud-init.html) for the script directory conventions). When the real lab VM boots, VyOS runs that persistent preconfig script after initial interface name resolution but before interface rescan and before the boot configuration is loaded. The script finds the netlab management interface by its `ca:fe:*` MAC address and deterministic netlab data interfaces by their `ca:f0:*` MAC addresses, writes matching `hw-id` bindings into the boot configuration, marks itself done, and triggers a reboot. On the next boot, VyOS uses those saved `hw-id` bindings to rename the interfaces before loading the configuration.

The packaged Vagrant box must not contain an `eth0` configuration node. Keeping `eth0` without `hw-id` makes VyOS treat it as a pending hardware binding; when a lab VM has multiple NICs, VyOS refuses to guess which NIC should inherit the `eth0` configuration and the boot fails. If you are reusing a disk from an earlier failed attempt, recreate the base qcow2 image before continuing.

```{eval-rst}
.. include:: vyos.txt
   :literal:
```

## Notes on Using the VyOS Box

The default Vagrant box name used by _netlab_ is `vyos-local/vyos`. When **netlab libvirt package** asks for a box version, use the VyOS image version or build ID, for example `2026.09.01-0034-rolling`.

If you still have the old `vyos/current` Vagrant box installed, it will not be used by default. To use it temporarily, set `defaults.devices.vyos.libvirt.image` to `vyos/current` in your topology or user defaults.
