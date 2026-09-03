(build-vyos)=
# Building a VyOS Libvirt Box

VyOS is supported by the **netlab libvirt package** command. The public `vyos/current` Vagrant box is no longer maintained; instead, build a local Vagrant box from a recent VyOS ISO image.

```{warning}
Building a VyOS Libvirt box is not straightforward, and this recipe is maintained on a best-effort basis. Use the VyOS containerlab image whenever possible.
```

The default Vagrant box name used by _netlab_ is `netlab/vyos`. When the **netlab libvirt package** command asks for a box version, use the VyOS image version or build ID, for example `2026.09.01-0034-rolling`.

The old `vyos/current` Vagrant box is no longer used as the default image. Set the `defaults.devices.vyos.libvirt.image` [default setting](topo-defaults) to `vyos/current` to use it ([more details](default-device-image)).

## Download a VyOS ISO Image

You can use any recent VyOS ISO image that supports the configuration syntax used by _netlab_. The usual public choices are:

* Download the latest VyOS rolling/nightly ISO image from the [VyOS rolling release builds](https://vyos.net/get/nightly-builds/) page.
* Download a VyOS Stream ISO image from the [VyOS download](https://vyos.io/) page if you prefer a less volatile public preview build.

VyOS publishes `.minisig` files for public images. Use the verification instructions on the VyOS download page to validate the ISO before installing it.

## Build the Vagrant Box

Execute **netlab libvirt package vyos _iso-image-name_** and follow the instructions.

```{warning}
If you're using a *netlab* release older than 1.8.2, or if you're using a Linux distribution other than Ubuntu, please [read the box-building caveats first](libvirt-box-caveats.md).
```

The box-building process has two stages:

* The VM with an empty disk is booted from the ISO image
* You start the VyOS installation process and reboot the VM
* The VM is booted from the virtual disk
* You mount the secondary CD-ROM and execute the final installation script

```{eval-rst}
.. include:: vyos.txt
   :literal:
```

## Behind the Scenes

The installation script copies _netsim_ firstboot script into the VM as `/config/scripts/vyos-preconfig-bootup.script`. When the lab VM boots from the Vagrant box, VyOS runs that persistent preconfig script after initial interface name resolution, but before interface rescan and before the boot configuration is loaded. The script finds the netlab management interface by its `ca:fe:*` MAC address and netlab data interfaces by their `ca:f0:*` MAC addresses, writes matching `hw-id` bindings into the boot configuration, marks itself done, and triggers a reboot. On the next boot, VyOS uses those saved `hw-id` bindings to rename the interfaces before loading the configuration.

## Notes on Using the VyOS Box

The default Vagrant box name used by _netlab_ is `netlab/vyos`. When **netlab libvirt package** asks for a box version, use the VyOS image version or build ID, for example `2026.09.01-0034-rolling`.

