(netlab-libvirt)=
# Libvirt Utilities

**netlab libvirt** performs these *libvirt*-related functions:

* **[package](netlab-libvirt-package)** -- create a Vagrant box from a VM virtual disk in `qcow2` or `vmdk` format.
* **[remove](netlab-libvirt-remove)** -- remove a Vagrant box and associated libvirt volume(s)
* **[config](netlab-libvirt-config)** -- display box building recipe.

```text
% netlab libvirt

Usage:

    netlab libvirt <action> <parameters>

The 'netlab libvirt' command can execute the following actions:

package   Help you create a Vagrant box from a qcow/vmdk virtual disk
config    Print the build recipe for the specified Vagrant box
remove    Remove the specified Vagrant box or related libvirt volumes

Use 'netlab libvirt <action> --help' to get action-specific help
```

(netlab-libvirt-package)=
## Building a Vagrant Box

The **netlab libvirt package** command:

* Creates a temporary build directory under the `/tmp` directory
* Copies the specified virtual disk into the build directory.
* Starts a VM from the copied virtual disk and connects your terminal to its console
* When you disconnect from the VM (follow the build recipe), stops and destroys the VM and builds a Vagrant box
* Asks you for the software version you're using and installs the Vagrant box

```text
usage: netlab libvirt package [-h] [-v] [-q]
              {arubacx,asav,csr,dellos10,eos,iosv,iosxr,nxos,routeros7,vptx,vsrx}
              disk

Package a virtual machine into a libvirt Vagrant box

positional arguments:
  {arubacx,asav,csr,dellos10,eos,iosv,iosxr,nxos,routeros7,vptx,vsrx}
                        Network device you want to create
  disk                  Virtual machine disk (vmdk or qcow2)

options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose logging (add multiple flags for increased verbosity)
  -q, --quiet           Report only major errors
```

(netlab-libvirt-remove)=
## Removing a Vagrant Box

The **netlab libvirt remove** command:

* Finds a Vagrant box to remove based on the box name or device name
* Uses **vagrant** command to remove the box from your Vagrant box directory
* Uses **virsh vol-delete** command to remove *libvirt* volume created from the Vagrant box.

```text
netlab libvirt remove -h
usage: netlab libvirt remove [-h] [--box BOX] [--version VERSION] [--cleanup]
                             [--pool POOL]
                             [{arubacx,asav,cat8000v,csr,cumulus,cumulus_nvue,dellos10,eos,fortios,frr,iosv,iosvl2,iosxr,linux,none,nxos,routeros,routeros7,sonic,vptx,vsrx,vyos}]

Remove a libvirt Vagrant box

positional arguments:
  {arubacx,asav,cat8000v,csr,cumulus,cumulus_nvue,dellos10,eos,fortios,frr,iosv,iosvl2,iosxr,linux,none,nxos,routeros,routeros7,sonic,vptx,vsrx,vyos}
                        Remove a Vagrant box for the specified device

options:
  -h, --help            show this help message and exit
  --box BOX             Specify the Vagrant box you want to remove
  --version VERSION     Specify the version of the Vagrant box you want to remove
  --cleanup             Remove the volume(s) related to the specified Vagrant box
  --pool POOL           Specify the libvirt storage pool ('default' usually works)
```

(netlab-libvirt-config)=
## Displaying Box-Building Recipe

Vagrant boxes are usually created from "unconfigured" VM disks supplied by device vendors. The **netlab libvirt package** command creates a VM from such a disk and expects you to stop the zero-touch provisioning (or a similar mechanism) and copy-paste the initial configuration to the virtual device.

The **netlab libvirt config** command displays the box-building recipe (they are also available as part of the [box-building instructions](libvirt-build-boxes))

```text
% netlab libvirt config -h
usage: netlab libvirt config [-h]
                             {eos,dellos10,fortios,nxos,iosxr,arubacx,sonic,cat8000v,asav,vptx,vsrx,routeros7,csr,iosvl2,iosv}

Display Vagrant network device box configuration guidelines

positional arguments:
  {eos,dellos10,fortios,nxos,iosxr,arubacx,sonic,cat8000v,asav,vptx,vsrx,routeros7,csr,iosvl2,iosv}
                        Network device you want to create

options:
  -h, --help            show this help message and exit
```
