(tutorial-release)=
# Selecting Network Devices' Software Release

*netlab* relies on *Vagrant* or *containerlab* to start the network devices' virtual machines or containers. The name of the Vagrant box or Docker container to start can be specified in system defaults, user defaults, or individual devices.

This document describes how to select the desired software release for your network devices. Given a box name (without a release), Vagrant uses the Vagrant box with the *highest* software release, while Docker insists on starting the container with the *exact* software release (unless you use the **:latest** tag). If the software release you used as a tag for your Docker containers does not match the _netlab_ defaults, you must modify the user defaults or the lab topology.

## Finding the Expected Box or Container Name

Use the **[netlab show images](netlab-show-images)** command to display the expected box/container names. You can limit the printout to a single device with the `-d` parameter.

For example, these are the container/box names _netlab_ release 1.9.0 uses for Arista EOS devices:

```
% netlab show images -d eos
eos image names by virtualization provider

┏━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ device ┃ clab         ┃ libvirt     ┃ virtualbox  ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ eos    │ ceos:4.32.1F │ arista/veos │ arista/veos │
└────────┴──────────────┴─────────────┴─────────────┘
```

Assuming you have multiple `arista/veos` Vagrant boxes installed, Vagrant uses the one with the highest version number.  For example, with the following Vagrant boxes installed on a server, Vagrant uses `arista/veos:4.31.2F`.

```
$ vagrant box list|grep eos
arista/veos                 (libvirt, 4.28.3M)
arista/veos                 (libvirt, 4.31.2F)
```

The Docker container names have to match _netlab_ image names exactly. For example, you have to change user defaults if you want to start Arista cEOS containers with _netlab_ release 1.9.0 (that expects cEOS release 4.32.1F) when you have the following containers installed:

```
$ docker image ls ceos
REPOSITORY   TAG       IMAGE ID       CREATED         SIZE
ceos         4.32.0F   6d16e2631f3e   3 months ago    2.4GB
ceos         4.31.3M   6ee4a0c42758   3 months ago    2.47GB
ceos         4.31.2F   6cd23d2d3b3c   5 months ago    2.47GB
ceos         4.29.2F   07d07431e26d   16 months ago   2.08GB
```

(tutorial-release-names)=
## Changing the Target Software Release

You can change the container/box name _netlab_ uses for a network device with the [user defaults](defaults-user-file) or with an [environment variable](defaults-env).

To change the user default settings:

* Create `~/.netlab.yml` _netlab_ user defaults file
* Add the following line to that file to change the container name:

```yaml
devices._device_.clab.image: _image_name
```

* Add the following line(s) to that file (depending on the virtualization provider you're using) to change the Vagrant box name (it may include the software release):

```yaml
devices._device_.libvirt.image: _image_name
devices._device_.virtualbox.image: _image_name
```

```{tip}
Vagrant box names do not have to include the image version. If you specify just the box name, Vagrant selects the latest (numerically highest) version. Container image names must include the image tag (version).
```

For example, to use the Arista EOS 4.28/4.29 release, add the following lines:

```yaml
devices.eos.clab.image: ceos:4.29.2F
devices.eos.libvirt.image: arista/veos:4.28.3M
```

To change the device software release with an environment variable, set the NETLAB_DEVICES_*DEVICE*\_CLAB_IMAGE or NETLAB_DEVICES_*DEVICE*\_LIBVIRT_IMAGE environment variable. For example, to (temporarily) use cEOS container release ceos:4.29.2F, execute the following command:

```
$ export NETLAB_DEVICES_EOS_CLAB_IMAGE=ceos:4.29.2F
```

## Changing the Software Release in Lab Topology

Sometimes, you want to test older (or newer) versions of networking software in a particular lab topology. To do that, [change the system defaults within the lab topology](defaults-topology):

* Add the settings from the previous sections to the lab topology.
* Prepend `defaults.` to the settings to tell _netlab_ you're changing the defaults.

For example, to use the Arista EOS 4.28/4.29 release in a single lab, add the following lines to the lab topology file:

```yaml
defaults.devices.eos.clab.image: ceos:4.29.2F
defaults.devices.eos.libvirt.image: arista/veos:4.28.3M
```

## Changing the Software Release for Individual Nodes

You can always specify the exact container/box you want to use on a network device with the **image** or **box** attribute. For example, to test how the Arista EOS 4.28.3M VM interacts with the Arista EOS 4.31.2F container, use the following topology file:

```
provider: libvirt

nodes:
  r1:
    device: eos
    image: arista/veos:4.28.3M
  r2:
    device: eos
    provider: clab
    image: ceos:4.31.2F
```

