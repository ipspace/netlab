# List of Configuration Modules

The following configuration modules are included in the **netlab** distribution:

```eval_rst
.. toctree::
   :maxdepth: 1

   module/bfd.md
   module/bgp.md
   module/dhcp.md
   module/eigrp.md
   module/evpn.md
   module/gateway.md
   module/routing.md
   module/isis.md
   module/lag.md
   MPLS Configuration Module (LDP, BGP-LU, MPLS/VPN) <module/mpls.md>
   module/ospf.md
   module/ripv2.md
   module/sr-mpls.md
   module/stp.md
   module/vrf.md
   module/vlan.md
   module/vxlan.md
```

```{tip}
* Use the **‌[netlab show modules](netlab-show-modules)** command to display the list of supported configuration modules and the devices each module supports.
* Use the **‌[netlab show module-support](netlab-show-module-support)** command to display configuration modules supported on individual devices.
* Use the **‌[netlab show modules --m _module_](netlab-show-modules)** command to display the device support for the module-specific features.
```

## Common Routing Protocol Features

```eval_rst
.. toctree::
   :maxdepth: 1

   module/routing_protocols.md
```

## Experimental Modules

Experimental modules are usually implemented on a small set of devices. We're also not (yet) entirely sure about the data model describing their features; it might change in future releases as we gain more experience with them.

```eval_rst
.. toctree::
   :maxdepth: 1

   module/srv6.md
```
