# OSPF Area Parameters Plugin

You can use the **ospf.areas** plugin to configure stub and NSSA areas, area ranges (summarization), or summarization of external NSSA (type-7) routes into external (type-2) routes. These features are considered core features as they're defined in RFC 2328, RFC 5340, and RFC 1587.

The plugin also supports suppressing inter-area routes in stub/NSSA areas, resulting in totally stubby/NSSA areas. This feature might not be available on all supported platforms.

## Supported Platforms

The plugin includes Jinja2 templates for the following platforms:

| Operating system    | Stub/NSSA<br>areas | Totally<br>stubby areas | Area ranges |
|--------------|:-:|:-:|:-:|
| Arista EOS   |✅ [❗](caveats-eos) |✅|✅|
| Cumulus NVUE |✅|✅|✅ [❗](caveats-cumulus-nvue) |
| Dell OS10    |✅|✅|✅ [❗](caveats-os10) |
| FRR          |✅|✅|✅ [❗](caveats-frr) |
| JunOS        |✅|✅|✅|
| SR Linux     |✅|✅|✅ [❗](caveats-srlinux) |

## Specifying OSPF Area Parameters

The OSPF area parameters can be specified in global-, node-, or VRF-level **ospf.areas** list. Each element of the list can have these attributes:

* **area** (mandatory) -- OSPF area ID in integer or IPv4 address format.
* **kind** -- OSPF area type (*stub*, *nssa*, or *regular*)
* **default.cost** (int) -- The cost of the default route inserted into the stub/NSSA area (IPv4 only)
* **inter_area** (bool, default: *true*) -- propagation of inter-area routes into stub/NSSA area. Set to *false* to implement totally stubby areas.
* **range** (list of IPv4 or IPv6 prefixes) -- summarization ranges for the area
* **filter** (list of IPv4 or IPv6 prefixes) -- not-advertized summarization ranges for the area
* **external_range** (list of IPv4 or IPv6 prefixes) -- NSSA summarization ranges for the external type-7 routes from this area
* **external_filter** (list of IPv4 or IPv6 prefixes) -- not-advertized summarization ranges for the external type-7 routes from this area

Example:

```
ospf.areas:
# Regular area with a summarization
# range and a no-advertise (filtering) range
# You can specify IPv4 and IPv6 prefixes in the
# same list.

- area: 11
  range:
  - 10.17.0.0/16
  - 2001:db8:1::/48
  filter:
  - 10.18.0.0/16
  - 2001:db8:2::/48

# Totally stubby area

- area: 51
  kind: stub
  inter_area: false
```

## Inheritance of Configuration Parameters

* Global (topology) **ospf.areas** definitions are merged with node **ospf.areas** definitions, allowing you to define OSPF area parameters for the whole lab topology.
* Node **ospf.areas** definitions are merged with the definitions in VRF instances.
* The merge of data is done on the attribute level. For example, the global **range** parameter would be *copied* into the node definition if the node definition does not contain that parameter, but will not be *appended* to an existing node-level **range** parameter.

You can set most parameters in the node- or VRF definition to *False* to prevent their inheritance.
