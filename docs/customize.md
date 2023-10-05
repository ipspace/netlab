# Customize netlab

_netlab_ is designed to be highly extensible and customizable. Starting with the system settings, you can:

* [Overwrite system defaults](defaults.md), either with user default files or in the lab topology.
* Change the [default device images](default-device-image) to run a specific software version in your lab.
* Change [system addressing pools](addressing.md) or define your own.

If you want to use _netlab_ to deploy additional device configuration you can:

* Use **[netlab config](netlab/config.md)** to add custom configuration to an already-provisioned lab.
* List your own configuration templates in [node](node-attributes)- or [group **config** attribute](custom-config) to configure functionality not yet supported by *netlab* during **[netlab up](netlab/up.md)** or **[netlab initial](netlab/initial.md)** process.
* [Define your own](extend-attributes.md) global-, node-, link- or interface attributes to parametrize your configurations.

You can also augment the _netlab_ data model transformation or add new functionality with [plugins](plugins.md).

(customize-templates)=
If you want to change the provisioning- or device configuration templates, you can:

* Create your own device configuration templates: copy a [system device configuration template](https://github.com/ipspace/netlab/tree/dev/netsim/ansible/templates) into **templates/_module_/_device_.j2** file[^MIN] and modify it. You can have custom device configuration templates in the current directory or in the `~/.netlab` directory.
* Create your own device provisioning template: copy a [system template](https://github.com/ipspace/netlab/tree/dev/netsim/templates) into **_provider_/_device_-domain.j2** file and modify it.

[^MIN]: Initial device configurations are stored in **templates/initial** directory.

Finally, you might want to use external tools or devices not yet supported by _netlab_:

* [Adding external tools](dev/extools.md) is relatively easy.
* If you want to add unsupported devices to a lab but are willing to configure them manually, just [define them as _unknown_ devices](platform-unknown).
* Adding [new functionality to an existing device](dev/device-features.md) or adding a new device to _netlab_ takes more effort. When adding a new device, it's easier to [define a new device](dev/device-box.md) and keep it _[unprovisioned](group-special-names)_ than going for a [full-blown implementation](dev/devices.md).

Regardless of how far you're willing to go, we'd appreciate if you decided to [contribute your changes](dev/guidelines.md), but it's perfectly fine to keep them private. The best part: you don't have to modify the _netlab_ package to get the job done; you could use [user defaults](defaults.md) to define new stuff, and user-defined configuration templates (see above) to configure it.

```eval_rst
.. toctree::
   :hidden:
   :maxdepth: 2

   extend-attributes.md
```
