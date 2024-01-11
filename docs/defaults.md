# Topology Defaults

*netlab* has dozens of system defaults that specify:

* Default [addressing pools](addressing.md)
* Default [virtualization provider](providers.md)
* [Module defaults](modules.md)
* Virtualization provider defaults (configuration file name, port mappings, provider-specific device defaults...)
* Device parameters (interface names, [image names](netlab-show-images)...) and [capabilities](netlab-show-modules)

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Changing Defaults

The system defaults are specified in the global **topology-defaults.yml** file (shipped with the *netlab* package). These defaults are imported into the lab topology under the **defaults** top-level attribute. They could be overwritten with the **defaults** element within the lab topology or from user- or system defaults files.

### Changing Defaults in Lab Topology

To change a default setting for a single lab topology, set **defaults.$something** attribute to the desired value in the lab topology file.

For example, if you want to change the current lab's default device (**defaults.device**) to Arista EOS, add `defaults.device: eos` to the lab topology file or use the expanded format:

```
defaults:
  device: eos
```

```{tip}
If you're a novice user, tweak the defaults with the lab topology settings, and migrate them to the user defaults file when you get the desired results.
```

(defaults-user-file)=
### Changing Defaults in User Defaults Files

Create a YAML file specifying user defaults if you want the same defaults changed for all your lab topologies. _netlab_ tries to find user defaults in the following files (but see also [](defaults-locations)):

* **topology-defaults.yml** file in the lab directory
* **.netlab.yml** file in the user home directory.
* System-wide **/etc/defaults/netlab.yml** file

The default settings in the user defaults files are identical to the ones you'd use in the network topology file but without the `defaults.` prefix[^MD].

[^MD]: If you're migrating defaults from a lab topology into a defaults file, remove the **defaults** prefix.

For example, to make sure all labs use Arista EOS as the default device type using a specific cEOS or vEOS image, create the following `.netlab.yml ` file in your home directory:

```
---
device: eos
devices.eos:
  clab.image: ceos:4.27.2F
  libvirt.image: arista/veos:4.28.3M
```

During the topology gathering process, _netlab_ reads the `~/.netlab.yml` file, converts it into a dictionary, and [merges it](defaults-deep-merging) with the **defaults** topology dictionary, resulting in the **defaults.device** entry in the lab topology data structure set to `eos`.

```{tip}
If you don't know what to change, explore the system defaults with the **‌netlab show defaults** command. See also [](defaults-debug).
```

(default-device-type)=
### Example: Changing Device Type and Device Image

The topology **defaults** value is most commonly used to set the default device type; you could also use it to set any other default parameter. For example, the following topology file builds a network of Cisco IOSv devices using a different value for the default IS-IS area:

```
---
defaults:
  device: iosv
  isis:
    area: 49.0002

...
```

When augmenting default settings, *netlab* uses a [deep dictionary merge](defaults-deep-merging), allowing you to overwrite a single setting deep in the defaults hierarchy without affecting other related settings. 

(default-device-image)=
For example, it's possible to replace the default Vagrant box name for a network device type without changing any other device parameter[^DD]:

[^DD]: See [](topology/hierarchy.md) for an in-depth explanation of why attributes with hierarchical names work in *netlab*

```
---
defaults.device: eos
defaults.devices.eos.image: arista/vEOS-lab-4.21.14M
```

Change the provider-specific device images if you want to run your topology on multiple virtualization providers. This is how you can set different device image names for Arista EOS virtual machines and containers:

```
---
defaults.device: eos
defaults.devices.eos.libvirt.image: arista/vEOS-lab-4.21.14M
defaults.devices.eos.clab.image: cEOS:latest
```

(defaults-debug)=
## Debugging User Default Files

You can debug the processing of the default files with the `--debug defaults` option of the **[netlab create](netlab/create.md)** command. You could use it when creating the lab configuration files or as `netlab create --output none --debug defaults` command if you want to do the debugging without creating any output.

Use the **[netlab show defaults](netlab-show-defaults)** command to investigate how the system defaults were augmented with the user defaults. For example, execute `netlab show defaults gateway` to inspect the settings of the **gateway** module or `netlab show defaults outputs.d2` to inspect the settings of the D2 graphing output module.

You can also use the **[netlab inspect defaults...](netlab/inspect.md)** command after you create the lab configuration files (and the snapshot file) with the **netlab create** or **[netlab up](netlab/up.md)** command. For example, to inspect the Arista EOS device settings, use **netlab inspect defaults.devices.eos**.

Finally, if you want to see how the lab topology defaults interact with user- and system defaults *without creating any output files*, use the **netlab create --output yaml:defaults...** command to process the lab topology and print the collected default values. For example, execute `netlab create --output yaml:defaults.addressing` to inspect the default address pools your lab topology would use.

## Advanced Topics

(defaults-deep-merging)=
### Deep Merging

*netlab* uses the Python Box package to perform a recursive merge of lab topology with user- and system defaults:

* Dictionary keys not present in the target dictionary are added from the **defaults** dictionary;
* Whenever a key in the target dictionary is itself a dictionary and the same key is present in the **defaults** dictionary, the merge process recurses, resulting in a recursive merge of child dictionaries.
* Lists and scalar values are not merged.

(defaults-locations)=
## Alternate Defaults Files Locations

By default, *netlab* tries to find:

* User default files in `./topology-defaults.yml`, `~/.netlab.yml` and `~/topology-defaults.yml`
* System defaults in `/etc/netlab/defaults.yml` and `package:topology-defaults.yml`

You can change the locations of user- or system defaults with the `defaults.sources` parameters specified in the lab topology file[^NAE]:

[^NAE]: These parameters cannot be changed anywhere else as they're checked before the default values are merged with the lab topology file.

* `defaults.sources.extra` adds files to the list of user default files. You can use this parameter to add extra defaults to larger projects with a hierarchical directory structure.
* `defaults.sources.list` (if present) specifies the complete list of default file locations that cannot be changed with other parameters
* `defaults.sources.user` changes the list of potential user default files.
* `defaults.sources.system` changes the list of potential system default files.

```{warning}
If you need to change the `defaults.sources.system` setting, make sure `package:topology-defaults.yml` is the last element in the list, or you'll face an interesting troubleshooting exercise.
```

For example, the [project-wide defaults file](https://github.com/ipspace/bgplab/blob/main/defaults.yml) in the [BGP Hands-On Labs](https://github.com/ipspace/bgplab/) project specifies the device type you want to use in the labs. Individual lab topologies ([example](https://github.com/ipspace/bgplab/blob/main/basic-session/topology.yml)) are stored in subdirectories and use `defaults.sources.extra` parameter to add project-wide defaults to the lab topology, for example:

```yaml
# Configure a BGP session with an external BGP speaker

defaults.sources.extra: [ ../defaults.yml ]

nodes:
  rtr:
  x1:
    device: cumulus
    module: [ bgp ]
    bgp.as: 65100

links:
- rtr-x1
```
