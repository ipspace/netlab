(link-example)=
# Link Definition Examples

This document contains way too many link definition examples, ranging from simple links to complex topologies emulating bridging loops.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

Some examples include the resulting internal data structure (link data dictionary with **interfaces** list) generated in an early phase of [topology transformation process](../dev/transform.md).

Read the [Concise Link Descriptions in netlab Topologies](https://blog.ipspace.net/2025/01/netlab-link-definitions/) and [Group Similar Links in netlab Topologies](https://blog.ipspace.net/2025/02/netlab-link-dictionary/) blog posts for even more details.

(link-example-no-attributes)=
## Simple Links with No Link Attributes

When you need a connection between lab devices with no extra attributes, use the *string format*.

### Stub Interface

```
nodes: [ r1 ]
links:
- r1
```

... creates a link with a single node attached to it. The resulting list has one entry with no other attribute than an **interfaces** list -- list of nodes connected to the link (identified by **node** attribute):

```
links:
- interfaces:
  - node: r1
```

### Point-to-Point Interface

Use a-b syntax to create a point-to-point link between nodes A and B:

```
nodes: [ r1,r2 ]
links:
- r1-r2
```

Not surprisingly, the **intefaces** list in the link definition has two nodes (r1 and r2):

```
- interfaces:
  - node: r1
  - node: r2
```

### Multi-Access Interface

You can extend the string syntax to multiple nodes, for example:

```
nodes: [ r1,r2,r3 ]
links:
- r1-r2-r3
```

Result:

```
- interfaces:
  - node: r1
  - node: r2
  - node: r3
```

### Node Names with Hyphens

You cannot use the hyphen-separated list of nodes if you use hyphens in node names. In that case, you can use the (slightly ungainly) list of nodes, for example:

```
nodes: [ r-1, r-2 ]
links:
- [ r-1, r-2 ]
```

### Crazy Scenarios

Finally, it's perfectly OK to have the same node connected to a link more than once. Here's a potential bridging loop in case you want to figure out how your device reacts to it:

```
nodes: [ r1 ]
links:
- r1-r1
```

Result:

```
- interfaces:
  - node: r1
  - node: r1
```

## Links with Link or Interface Attributes

You can cover simple lab topologies with the *string format*, but you'll quickly get to a point where you'll want to specify additional link attributes. To do that, you must use a *dictionary* link description format.

A *dictionary* format is always translated into the canonical format with an **interfaces** list. However, that format is a bit cumbersome; using a simplified format specifying nodes connected to the link as dictionary keys is much better.

```{warning}
You cannot use the dictionary format if you want to have the same node attached to a link multiple times.
```

### Stub Link with OSPF Area

Imagine a multi-area OSPF topology where you want to put stub links into different OSPF areas:

```
module: [ ospf ]
nodes: [ r1 ]
links:
- r1:
  ospf.area: 3
```

Keys in the link dictionary are checked against node names. Nodes are moved into the **interfaces** list, and the other elements are left unchanged.

```
links:
- interfaces:
  - node: r1
  ospf:
    area: 3
```

### Links with Multiple Nodes

The same approach can be used for point-to-point and multi-access links. The following topology file...

```
nodes: [ r1,r2,r3 ]
links:
- r1:
  r2:
  r3:
  bandwidth: 3
```

... generates this data structure:

```
links:
- bandwidth: 3
  interfaces:
  - node: r1
  - node: r2
  - node: r3
```

### Using Simplified Interfaces List

You can list the nodes attached to a link in an **interfaces** list instead of declaring them as dictionary keys. For example, you can rewrite the above example as:

```
nodes: [ r1, r2, r3 ]
links:
- interfaces: [ r1, r2, r3 ]
  bandwidth: 3
```

(link-interface-attribute)=
### Links with Interface Attributes

Each interface (node-to-link attachment) can have its attributes specified as a dictionary under the node key. For example, you might want to set OSPF cost and disable BFD for a single node on a multi-access link:

```
module: [ ospf,bfd ]
nodes: [ r1,r2,r3 ]
links:
- r1:
    ospf.cost: 5
    ospf.bfd: False
  r2:
  r3:
  bandwidth: 3000
```

The link attributes are retained (as before); the nodes and their attributes are moved into the **interfaces** list:

```
links:
- bandwidth: 3000
  interfaces:
  - node: r1
    ospf:
      bfd: false
      cost: 5
  - node: r2
  - node: r3
```

## Complex Scenarios

If you want to have link (or interface) attributes in a complex scenario with multiple connections from a node to a link, you have to use the dictionary-with-interfaces format, for example:

```
links:
- bandwidth: 3000
  interfaces:
  - node: r1
  - node: r1
```

You can freely combine all three formats, for example:

```
nodes: [ r1, r2, r3 ]

links:
- r1
- r1-r2
- r1:
  r3:
  type: lan
- interfaces:
  - node: r1
  - node: r1
  bandwidth: 3000
```

