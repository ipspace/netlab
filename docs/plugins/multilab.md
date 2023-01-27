# Running Multiple Labs on Linux Servers

Using the default settings, _netlab_ cannot run more than a single lab instance on a Linux server -- it relies on default network names and IP prefixes used by *vagrant-libvirt* plugin and *containerlab* orchestration system.

The *multilab* plugin modifies virtualization defaults for every lab instance, allowing you to run multiple *libvirt*- or container-based labs in parallel. Using its default settings, the plugin modifies:

* Lab **name** that is used as a prefix for VM-, container, and bridge names.
* Name of the management network and underlying Linux bridge
* IP prefix of the management network.

The plugin has been tested with **[libvirt](../labs/libvirt.md)** and **[clab](../labs/clab.md)** _netlab_ virtualization providers.

```{warning}
While you can use the same topology file for multiple lab instances, you MUST run each lab instance in a different working directory.
```

## Using the Plugin

You can use *multilab* plugin in three scenarios:

**Static instances:** you want to run different lab topologies in parallel, but not multiple instances of the same lab. Specify **defaults.multilab.id** in the lab topology and add *multilab* plugin with the lab topology **plugin** parameter.

```
# Lab topology using multilab plugin
#
plugin: [ multilab ]
provider: libvirt

defaults.multilab.id: 12
```

**Per-user instances:** you have multiple users using the same Linux servers. Each user is allowed to run one lab at a time. Specify **multilab.id** in [user defaults file](../defaults.md) and activate *multilab* plugin with the **plugin** parameter in the same file.

```
# User defaults file activating multilab plugin
#
plugin: [ multilab ]
multilab.id: 12
```

**Dynamic labs:** Users can run multiple lab instances or multiple instances of the same lab topology. You will have to handle allocation of lab instances with an external system that passes **defaults.multilab.id** to _netlab_ with the `-s` argument of **[netlab create](../netlab/create.md)** or **[netlab up](../netlab/up.md)** command. The best way to activate the *multilab* plugin is with the `--plugin` CLI argument.

```
# Start the lab with multilab plugin
#
netlab up --plugin multilab -s defaults.multilab.id=12 topology.yml
```


## Behind the Scenes

*multilab* plugin uses *lab id* specified in **defaults.multilab.id** to change system defaults or topology parameters listed in **defaults.multilab.change** dictionary. The default parameters *multilab* plugin changes are specified in `netsim/defaults/multilab.yml` file; you can add your own parameters if needed.

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

The plugin modifies the way _netlab_ creates Linux bridge names and interface names. The maximum length of a Linux interface name 15 characters, limiting the length of prefix taken from topology **name** parameter to form interface/bridge names:

* The bridge name of the management network cannot be longer than 15 characters.
* Linux bridge names used for multi-access links are created from the first 10 characters of **name** parameter followed by **linkindex**
* Names of container interfaces connected to Linux bridges are created from the first 6 characters of **name** parameter followed by node **id** and interface **ifindex**.
* Names of *libvirt* interfaces connected to Linux bridges are composed of **vifprefix**, node **name** and interface **ifindex**. As the interface names cannot be longer than 15 characters, the *libvirt* interface name is not set if the resulting string is longer than that -- *libvirt* will use an internally-generated interface name.

```{warning}
The first 6 characters of lab topology **name** generated from _multilab_ **change** dictionary must be unique or you'll have duplicate container interface addresses resulting in failed _containerlab_ deployment. In a _libvirt_-only environment, the first 10 characters of lab topology **name** must be unique.
```
