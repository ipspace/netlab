# Running Multiple Labs on Linux Servers

Using the default settings, _netlab_ cannot run more than a single lab instance on a Linux server -- it relies on default network names and IP prefixes used by *vagrant-libvirt* plugin and *containerlab* orchestration system.

The *multilab* plugin modifies virtualization defaults for every lab instance, allowing you to run multiple *libvirt*- or container-based labs in parallel. Using its default settings, the plugin modifies:

* Lab **name** that is used as a prefix for VM-, container, and bridge names.
* Name of the management network and underlying Linux bridge
* IP prefix of the management network.

The plugin has been tested with **[libvirt](../labs/libvirt.md)** and **[clab](../labs/clab.md)** _netlab_ virtualization providers.

## Using the Plugin

You can use *multilab* plugin in three scenarios:

* Static instances -- **defaults.multilab.id** is specified in the lab topology. *multilab* plugin is specified in the lab topology **plugin** parameter.

```
# Lab topology using multilab plugin
#
plugin: [ multilab ]
provider: libvirt

defaults.multilab.id: 12
```

* Per-user instances -- **multilab.id** is specified in [user defaults file](../defaults.md). *multilab* plugin is specified in the **plugin** parameter in the same file.

```
# User defaults file activating multilab plugin
#
plugin: [ multilab ]
multilab.id: 12
```

* Dynamic labs -- **defaults.multilab.id** is specified with the `-s` CLI parameter of **[netlab create](../netlab/create.md)** or **[netlab up](../netlab/up.md)** command. *multilab* plugin is added to the topology with the `--plugin` CLI parameter.

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
  addressing.mgmt:
    ipv4: '192.168.{id}.0/24'
    _network: 'nl_mgmt_{id}'
    _bridge:  'nl_mgmt_{id}'
```

String values specified in the **defaults.multilab.change** dictionary are evaluated as f-formatted Python strings. You can use the **id** variable (the value of **defaults.multilab.id** parameter) or any lab topology parameter (including system defaults) in the evaluated expressions.