# Custom Attributes

*netlab* [topology file transformation](dev/transform.md) validates most of the global, link, and module attributes to prevent hard-to-find typing errors. Node attributes are not yet checked.

To extend the lab topology with custom attributes (examples: BGP anycast prefix, DMZ bandwidth, OSPF stub areas...) you have to define the custom attributes (keywords) you want to be recognized.

Custom global and link attributes are defined in **defaults.extra_attributes** dictionary which can have the following elements:

* **global** -- valid top-level elements
* **link** -- valid link attributes
* **link_no_propagate** -- link attributes that are not copied into node interface data structures. This list must be a subset of **link** list.

The values of all elements of the **defaults.extra_attributes** dictionary should be lists of strings.

```{tip}
After defining custom attributes you have to create additional Jinja2 templates that use these attributes to configure additional lab device functionality.

You can deploy those templates during initial lab device configuration with [custom configuration templates](groups.md#custom-configuration-templates) or use **‌netlab config** command to deploy them manually.
```

## Example: DMZ bandwidth

Imagine a lab topology in which you want to define external (DMZ) bandwidth on individual links. To do that, set the **defaults.extra_attributes.link** parameter to create an additional link attribute:

```
defaults:
  device: iosv
  extra_attributes:
    link: [ dmz ]

nodes: [ e1, e2, pe1 ]

links:
- e1:
  e2:
  dmz: 100000
- e2:
  pe1:
```

## Extending Module Attributes

The lists of valid global-, node- and link attributes of every configuration are specified in **_module_.attributes** dictionary in *topology-defaults.yml* system configuration file.

Extending module attributes is identical to extending global attributes: set **_module_.extra_attributes._type_** to a list of custom attributes. The _type_ parameter can be:

* **global** -- Global module parameters. These parameters are copied into node data structures.
* **node** -- Module parameters that can be set on individual nodes (but not globally)
* **link** -- Module parameters that can be set on individual links.

For example, this is how you can add **bgp.anycast** node attribute to the lab topology:

```
module: [ ospf, bgp ]

defaults:
  device: iosv
  bgp.extra_attributes.node: [ anycast ]

bgp.as: 65000

nodes: 
  l1:
  l2:
    bgp.anycast: 10.42.42.42/32

links: [ l1-l2 ]
```

Some modules have no configurable attributes. You can use the same mechanism to add module attributes to such modules. For example, the following topology description adds node ID to [SR-MPLS](module/sr-mpls.md):

```
module: [ sr,isis ]

defaults:
  device: csr
  sr.extra_attributes.node: [ id ]

nodes: 
  l1:
    sr.id: 101
  l2:
    sr.id: 102

links: [ l1-l2 ]
```
