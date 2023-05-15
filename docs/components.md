# Topology Components

Large lab topologies tend to be structured. For example, you might have two sites with a leaf-and-spine fabric, or a leaf-and-spine fabric with multiple racks.

Topology *components* allow you to define reusable smaller structures that you can include multiple times into the same lab topology.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Defining Components

Topology components are defined in the **components** dictionary. Each value in that dictionary should have **nodes** element (nodes within the component), **links** list (intra-component links) and any other attribute that is a valid node-level attribute, for example BGP AS number.

Imagine you have a lab topology with multiple sites, and each site has a PE-router and a P-router. The site structure could be defined as a component:

* It has two nodes (P and PE)
* P-router runs OSPF and MPLS
* PE-router runs OSPF, BGP, and MPLS
* The default OSPF cost for intra-site links is 100
* The default BGP AS number is 65000

```
components:
  site:
    nodes:
      p:
        module: [ ospf, mpls ]
      pe:
        module: [ ospf, bgp, mpls ]
    links: [ p-pe ]
    ospf.cost: 100
    bgp.as: 65000
```

## Using Components

Use **include** node attribute to include a component into the topology. You can add any node-level attribute you wish to the node with the **include** attribute; such attributes will be copied to the nodes created from the included component.

For example, use the following **nodes** dictionary to build a lab topology with three sites (each of them defined as a *site* component), and set different default OSPF cost for the third site (S3):

```
nodes:
  s1:
    include: site
  s2:
    include: site
  s3:
    include: site
    ospf.cost: 200
```

## Including Components

Whenever you include a component into a lab topology, _netlab_ creates new nodes, links, and a component-specific group that includes component- and parent node settings. The node names of the new nodes are composed from the parent node name and the component node name.

```{tip}
It's easy to exceed the maximum node name length (16 characters) when using lab components. To increase the maximum node name length, set the `defaults.const.MAX_NODE_ID_LENGTH` lab topology attribute (see also: [changing defaults](defaults.md)).
```

The above three-site lab topology would result in:

* Six nodes: s1_p, s1_pe, s2_p, s2_pe, s3_p, and s3_pe
* Three links: s1_p-s1_pe, s2_p-s2_pe, and s3_p-s3_pe
* Three groups: inc_s1, inc_s2 and inc_s3

The inc_s3 group would have two members (s3_p and s3_pe) and two node parameters: **ospf.cost** set to 200 (copied from the *s3* node) and **bgp.as** set to 65000 (copied from the *site* component).

As the final stage of a component expansion, the parent node is removed from the list of nodes.

## Inter-Component Links

The **links** element within a component can refer only to nodes within the same (or child) component. Links between components must be specified outside of the components (for example, in the global **links** list) and must use the expanded name of the nodes.

For example, the following list of links describes the connectivity between our three sites:

```
links: [ s1_p-s2_p, s2_p-s3_p, s3_p-s1_p ]
```

