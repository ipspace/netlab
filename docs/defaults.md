# Topology Defaults

*netlab* has dozens of system defaults that specify:

* Default [addressing pools](addressing.md)
* Default virtualization provider
* [Module defaults](modules.md)
* Virtualization provider defaults (configuration file name, port mappings, provider-specific device defaults...)
* Device parameters (interface names, image names...) and capabilities

All system defaults specified in the global **topology-defaults.yml** file (shipped with *netlab* package) could be overwritten with topology- or user defaults:

* With **defaults** element of the topology file
* From **topology-defaults.yml** file residing in the same directory as the topology file or in the user's home directory.
* From **.netlab.yml** file residing in user's home directory

(default-device-type)=
The topology **defaults** value is most commonly used to set default device type; you could also use it to set any other default parameter. For example, the following topology file builds a network of Cisco IOSv devices using a different value for the default IS-IS area:

```
---
defaults:
  device: iosv
  isis:
    area: 49.0002

...
```

When augmenting default settings, *netlab* uses a [deep dictionary merge](defaults-deep-merging), allowing you to overwrite a single setting deep in the hierarchy without affecting any other related settings. 

(default-device-image)=
For example, it's possible to replace the default Vagrant box name for a network device type without changing any other device parameter[^DD]:

[^DD]: See [](topology/hierarchy.md) for an in-depth explanation of why attributes with hierarchical names work in *netlab*

```
---
defaults.device: eos
defaults.devices.eos.image: arista/vEOS-lab-4.21.14M
```

**Note:** If you want to run your topology on multiple virtualization provides, you can set different device image name for every virtualization provider:

```
---
defaults.device: eos
defaults.devices.eos.libvirt.image: arista/vEOS-lab-4.21.14M
defaults.devices.eos.clab.image: cEOS:latest
```

(defaults-deep-merging)=
## Deep Merging

*netlab* uses Python Box package to perform recursive merge of configuration dictionaries:

* Dictionary keys not present in target dictionary are added from the defaults dictionary;
* Whenever a key in the target dictionary is itself a dictionary, and the same key is present in the defaults dictionary, the merge process recurses, resulting in a recursive merge of child dictionaries.
* Lists and scalar values are not merged.

(defaults-user-file)=
## User Default Settings

*netlab* reads system defaults from the system **topology-defaults.yml** and augments them with:

* **topology-defaults.yml** file in the lab directory
* **.netlab.yml** file in the user home directory.

The defaults setting in the user defaults files are identical to the ones you'd use in the network topology file but without the **defaults.** prefix -- *netlab* merges user default settings with system default settings.

For example, to make sure all labs use Arista EOS as the default device type using a specific cEOS or vEOS image, create the following **.netlab.yml** file in your home directory:

```
---
device: eos
devices.eos:
  clab.image: ceos:4.27.2F
  libvirt.image: arista/veos:4.28.3M
```
