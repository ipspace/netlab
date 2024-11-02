(plugin-multilab)=
# Running Multiple Labs on Linux Servers

Using the default settings, *netlab* cannot run more than a single lab instance on a Linux server as it relies on the default network names and IP prefixes used by the *vagrant-libvirt* plugin and *containerlab* orchestration system.

The *multilab* plugin modifies virtualization defaults for every lab instance, allowing you to run multiple *libvirt*- or container-based labs in parallel. Using its default settings, the plugin modifies:

* Lab **name** that is used as a prefix for VM-, container, and bridge names.
* Name of the management network and underlying Linux bridge
* IP prefix of the management network.

The plugin has been tested with **[libvirt](../labs/libvirt.md)** and **[clab](../labs/clab.md)** _netlab_ virtualization providers.

```{warning}
* While you can use the same topology file for multiple lab instances, you MUST run each lab instance in a different working directory.
* The *‌multilab* plugin changes the lab topology parameters *‌after* the topology file, user- and system [defaults](defaults) have been processed. You cannot change a parameter controlled by the *‌multilab* plugin with a topology file setting; you must change the corresponding **defaults.multilab.change** parameter. See also [](multilab-behind-the-scenes)
```

## Using the Plugin

You can use *multilab* plugin in three scenarios:

**Static instances:** You want to run different lab topologies in parallel but not multiple instances of the same lab. Specify **defaults.multilab.id** in the lab topology and add the *multilab* plugin with the lab topology **plugin** parameter.

```
# Lab topology using the multilab plugin
#
plugin: [ multilab ]
provider: libvirt

defaults.multilab.id: 12
```

**Per-user instances:** You have multiple users using the same Linux servers. Each user is allowed to run one lab at a time. Specify **multilab.id** in the [user defaults file](../defaults.md) and activate the *multilab* plugin with the **plugin** parameter in the same file.

```
# User defaults file activating multilab plugin
#
plugin: [ multilab ]
multilab.id: 12
```

```{warning}
Use the system-wide _netlab_ status file if multiple users start lab instances on the same Linux server. You can change the location of the status file with the **‌defaults.lab_status_file** parameter.

All _netlab_ users should be able to write to the _netlab_ status file and the parent directory.
```

**Dynamic labs:** Users can run multiple lab instances, including several instances of the same lab topology. Each instance still needs a unique multilab ID that has to be allocated by an external system that passes **defaults.multilab.id** to _netlab_.

```{tip}
Each lab instance must be started in a different working directory. However, you can use the same lab topology file.
```

You can use the `-s` argument of **[netlab create](../netlab/create.md)** or **[netlab up](../netlab/up.md)** command to set **defaults.multilab.id**. Use the `--plugin multilab` CLI argument when specifying the multilab ID with the `-s` argument.

```
# Start the lab with the multilab plugin
#
netlab up --plugin multilab -s defaults.multilab.id=12 topology.yml
```

You can also use the _netlab_ environment variables to specify the default plugin(s) to use and the multilab ID. For example:

```
$ export NETLAB_PLUGIN=multilab
$ export NETLAB_MULTILAB_ID=17
```

(multilab-behind-the-scenes)=
## Behind the Scenes

*multilab* plugin uses *lab id* specified in **defaults.multilab.id** to change system defaults or topology parameters listed in **defaults.multilab.change** dictionary. The default parameters *multilab* plugin changes are specified in the `netsim/defaults/multilab.yml` file; you can add your parameters if needed.

```
change:
  name: 'ml_{id}'
  defaults.name: 'ml_{id}'
  defaults.providers.libvirt.tunnel_id: '{id}'
  defaults.providers.libvirt.vifprefix: 'vif_{id}'
  addressing.mgmt:
    ipv4: '192.168.{id}.0/24'
    _network: 'nl_mgmt_{id}'
    _bridge:  'nl_mgmt_{id}'
```

String values specified in the **defaults.multilab.change** dictionary are evaluated as f-formatted Python strings. You can use the **id** variable (the value of **defaults.multilab.id** parameter) or any lab topology parameter (including system defaults) in the evaluated expressions.

## Interface Name Limitations

The plugin modifies how _netlab_ creates Linux bridge and interface names. The maximum length of a Linux interface name is 15 characters, limiting the size of the prefix taken from the topology **name** parameter to form interface/bridge names:

* The bridge name of the management network cannot be longer than 15 characters.
* Linux bridge names used for multi-access links are created from the first ten characters of the **name** parameter followed by the **linkindex** value.
* The names of container interfaces connected to Linux bridges are created from the first six characters of the **name** parameter followed by node **id** and interface **ifindex**.
* The names of *libvirt* interfaces connected to Linux bridges are composed of **vifprefix**, node **name** and interface **ifindex**. As the interface names cannot be longer than 15 characters, the *libvirt* interface name is not set if the resulting string is longer than that (*libvirt* will use an internally-generated interface name).

```{warning}
The first six characters of the lab topology **name** generated from the _multilab_ **change** dictionary must be unique. Otherwise, _netlab_ generates duplicate container interface names in failed _containerlab_ deployments. In a *libvirt*-only environment, the first ten characters of the lab topology **name** must be unique.
```
