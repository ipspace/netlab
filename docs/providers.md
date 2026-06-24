(providers)=
# Virtualization Providers

*netlab* uses third-party orchestration and virtualization tools to create, start, stop, and destroy virtual labs. It supports the following virtualization providers:

* **[libvirt](labs/libvirt.md)** -- *libvirt* virtualization abstraction layer (tested on top of KVM/QEMU on Ubuntu) orchestrated with Vagrant using *vagrant-libvirt* Vagrant plugin.
* **[clab](labs/clab.md)** -- Docker containers (tested on Ubuntu) orchestrated with *containerlab*.
* **[external](labs/external.md)** -- meta-provider you can use to configure hardware devices.

```{note}
* The **virtualbox** provider is no longer available. Use _netlab_ release 26.06 or earlier if you want to use _VirtualBox_.
* Use **[‌netlab show providers](netlab-show-providers)** command to display the available virtualization providers.
```

You can also combine [multiple virtualization providers](labs/multi-provider.md) within the same lab topology (some restrictions apply).

```eval_rst
.. toctree::
   :caption: More Information on Virtualization Providers
   :maxdepth: 1

   labs/libvirt.md
   labs/clab.md
   labs/external.md
   labs/multi-provider.md
```

