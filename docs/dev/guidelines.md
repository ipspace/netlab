# Contributor Guidelines

Contributing to *netlab* is as easy as it can get:

* Create a fork of the [GitHub repository](https://github.com/ipspace/netlab).
* Make the changes.
* Run tests (`tests/run-tests.sh`) just to make sure you haven't broken anything.
* Submit a pull request *against the **dev** branch*

The easiest way to get started is to [add support for a new platform for an existing device](device-platform.md). [Contributing a new device](device-box.md) that is not configurable is also an easy task.

[Adding functionality to an existing device](device-features.md) is a bit more complex, while [contributing a new device](devices.md) (including configuration task lists and templates) might take a non-trivial amount of time.

```eval_rst
.. toctree::
   :maxdepth: 1
   :caption: More Information

   device-platform.md
   device-box.md
   device-features.md
   devices.md
   unnumbered.md
```

```eval_rst
.. toctree::
   :maxdepth: 1
   :caption: Implementation Notes

   config/deploy.md
   config/initial.md
   config/ospf.md
   config/bfd.md
   config/vlan.md
   config/vrf.md
```

```eval_rst
.. toctree::
   :maxdepth: 1
   :caption: Advanced Topics

   groups-pre-transform.md
   vlan-vrf-vxlan-evpn-transform.md
```
