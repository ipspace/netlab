(plugin-ospf-stub)=
# Fine-grained Control Over OSPF Area Route Propagation

The **ospf.stub** plugin extends OSPF topology modeling by adding native support for stub, totally stubby, NSSA, 
and totally NSSA areas. These specialized OSPF area types are commonly used to simplify routing in enterprise networks 
by reducing the number of LSAs exchanged and minimizing routing table size in remote or branch locations. With this 
plugin, Netlab will automatically generate the correct configurations on all routers in the area, including the 
appropriate ABR settings. This makes it easy to model and validate optimized OSPF designs in your lab topologies.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Platform support

| Operating system    | Stub areas |
|---------------------|:----------:|
| Cumulus 5.x NVUE    |     ✅     |
| Dell OS10           |     ✅     |
| FRR                 |     ✅     |

## Using the Plugin

To use the plugin, add it to the **plugin** list in the lab topology:

```
plugin: [ ...., ospf.stub ]
```

This enables support for ospf.areas:

```
module: [ ospf ]

ospf.areas:
  1:
    kind: stub
    no_summarize: True
```
