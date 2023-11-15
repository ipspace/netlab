# Custom Attributes

*netlab* [topology file transformation](dev/transform.md) validates global, node, link, interface, module, address pool, VLAN, and VRF attributes to prevent hard-to-find typing errors.

To extend the lab topology with custom attributes (examples: BGP anycast prefix, DMZ bandwidth, OSPF stub areas...), you must define the custom attributes (keywords) you want to be recognized.

To define new attributes, add them to the relevant **attributes** dictionary -- see [](dev/validation.md) for more details. With this approach, you can also define the attribute type, which can then be used during the validation phase to check the attribute value.

After defining custom attributes, you usually have to create additional Jinja2 templates that use these attributes to configure additional lab device functionality. You can deploy those templates during initial lab device configuration with [custom configuration templates](custom-config) or use **‌[netlab config](netlab/config.md)** command to deploy them manually.

## Link Attribute Example

For example, to add **dmz** attribute (an integer value) to a link to specify DMZ bandwidth, use:

```
defaults.attributes.link.dmz: int
```

The **dmz** attribute will be copied from the link definition to all interfaces connected to that link, so you can use it in your custom configuration template.

## Node Attribute Example

To add **dns.server** node attribute (an IPv4 address), use:

```
defaults.attributes.node.dns.server: { type: ipv4, use: address }
```

## Extending Module Attributes

The lists of valid global-, node- and link attributes of every configuration are specified in **_module_.attributes** dictionary in the system defaults.

Extending module attributes is identical to extending global attributes: define a new key/value pair in the **_module_.attributes._type_** dictionary.The _type_ parameter can be:

* **global** -- Global module parameters. These parameters are copied into node data structures.
* **node** -- Module parameters that can be set on individual nodes (but not globally).

```{hint}
Global module parameters should also be defined as node parameters.
```

* **link** -- Module parameters that can be set on individual links. These parameters are also copied into interfaces
* **interface** -- Module parameters that can only be set on individual interfaces (node-to-link attachments)

For example, this is how you could add **bgp.anycast** node attribute to the lab topology:

```
defaults.bgp.attributes.node.anycast:
```

The attribute would be accepted, but its value would not be checked. It's much better to define the type of the attribute value (assuming _netlab_ supports it), for example:

```
defaults.bgp.attributes.node.anycast: { type: ipv4, use: prefix }
```

After you defined a new module attribute, you can use it in the lab topology, for example:

```
module: [ ospf, bgp ]

defaults:
  device: iosv
  bgp.attributes.node.anycast: { type: ipv4, use: prefix }

bgp.as: 65000

nodes: 
  l1:
  l2:
    bgp.anycast: 10.42.42.42/32

links: [ l1-l2 ]
```

However, while defining new attributes impacts the final device data model, it won't change device configurations -- you have to use [custom configuration templates](custom-config) to do that.
