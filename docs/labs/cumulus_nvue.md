(build-cumulus-nvue)=
# Installing a Cumulus Linux 5.x Vagrant Box

Community versions of Cumulus Linux 5.x Vagrant boxes were available for automatic download from Vagrant Cloud. The last community release is Cumulus Linux 5.10.0, which is no longer directly usable due to the default password expiration policy ([workaround](cumulus-nvue-pwd-fix)).

Newer versions of Cumulus Linux 5.x Vagrant boxes can be [downloaded from the NVIDIA website](https://www.nvidia.com/en-eu/networking/ethernet-switching/cumulus-vx/) after creating an account.

## Installing NVIDIA Vagrant Boxes

* [Download](https://www.nvidia.com/en-us/networking/ethernet-switching/cumulus-vx/download/) the desired version of Cumulus Linux (select the `Vagrant(libvirt)` image).
* Install the downloaded Vagrant box with the **vagrant box add _filename_ --name CumulusCommunity/cumulus-vx**

**Warnings:**

* You cannot set a box version on a Vagrant box added with the **vagrant box add** command ([workaround](cumulus-nvue-release)).
* If you want to switch to a different version of Cumulus Linux, you have to remove the current Vagrant box, delete the corresponding libvirt volume, and add a different box ([more details](libvirt-box-replace)).
* NVIDIA boxes have the same default password expiration policy as the community boxes and will stop working after 6 months.

(cumulus-nvue-release)=
## Setting the Release Version on Vagrant Boxes

If you want to set a software release version on a Cumulus Linux box downloaded from the NVIDIA web site:

* Create `box.json` file with the following content in the directory with the Vagrant box:

```
{
  "name": "CumulusCommunity/cumulus-vx",
  "description": "Cumulus Linux",
  "versions": [
    {
      "version": "5.6.6",
      "providers": [
        {
          "name": "libvirt",
          "url": "file://...absolute path"
        }
      ]
    }
  ]
}
```

* Change the **version** field to match the downloaded box.
* Use **realpath _box_filename_** to get the absolute path of the `.box` file
* Add the absolute path of the `.box` file to the **url** field (you should have three slashes after `file:`)
* Install the Vagrant box with **vagrant box add box.json**

(cumulus-nvue-pwd-fix)=
## Changing the Password Expiration Policy

Cumulus Linux 5.x boxes have a default 180 day password expiration policy for the *vagrant* account, resulting in "The configured shell (config.ssh.shell) is invalid and unable
to properly execute commands." error during **vagrant up** processing.

You can use this procedure to patch a disk image contained in a Vagrant box to change the default password expiration policy. 

```{tip}
The procedure was tested on an Ubuntu server with the default *libvirt/KVM* installation. You might have to adapt it for other Linux distributions or libvirt installations with custom storage pools
```

1. Install the Cumulus Linux Vagrant box or rely on automatic download of community version of Cumulus Linux 5.10.0.
2. Create `topology.yml` file in an empty directory with the following contents:

```
nodes:
  cl:
    provider: libvirt
    device: cumulus_nvue
```

3. Execute `netlab up`. If the VM starts, you don't have a problem (yet)
4. Cleanup the directory with `netlab down --cleanup`.
5. Install GuestFS tools: ```sudo apt install guestfs-tools```
6. Find out where Vagrant put the base box volume: ```virsh vol-list --pool default|grep CumulusCommunity```, for example:

```text
$ virsh vol-livirsh vol-list --pool default|grep
 CumulusCommunity-VAGRANTSLASH-cumulus-vx_vagrant_box_image_5.10.0_box.img   /var/lib/libvirt/images/CumulusCommunity-VAGRANTSLASH-cumulus-vx_vagrant_box_image_5.10.0_box.img
 CumulusCommunity-VAGRANTSLASH-cumulus-vx_vagrant_box_image_5.9.2_box.img    /var/lib/libvirt/images/CumulusCommunity-VAGRANTSLASH-cumulus-vx_vagrant_box_image_5.9.2_box.img
```

7. Copy the absolute path to the disk image file (second column).
8. Disable password expiration for the image: ```sudo virt-customize --run-command "chage -M -1 vagrant" -a [qcow2-path]``` where the \[qcow2-path\] is the absolute path of the disk image.
