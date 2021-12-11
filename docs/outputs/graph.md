# Topology Graph Output Module

*graph* output module create a description of network topology in [*graphviz* DOT format](https://graphviz.org/doc/info/lang.html). You can use that description with *graphviz* commands to create topology diagrams in [numerous output formats](https://graphviz.org/docs/outputs/).

**Note**: The network topology graph description contains nodes and links but no placement information. *graphviz* is pretty good at figuring out how to draw the required graph, but it pays out to test out various [layout engines](https://graphviz.org/docs/layouts/) (hint: use the name of the layout engine as the [CLI command](https://graphviz.org/doc/info/command.html)).

The *graph* output module is invoked by specifying `-o graph` parameter in **netlab create** command. It takes an optional destination file name (default: `graph.dot`).

A single formatting modifier can be used to specify the graph type:

* **topology** (default) -- Include, physical links, and multi-access- and stub subnets. When the network topology contains BGP information, the graph groups nodes into autonomous systems.
* **bgp** -- Include autonomous systems, nodes, and BGP sessions.

## Modifying Graph Attributes

Graphing routines use **default** topology settings to modify the node- or link parameters of the generated DOT file:

* **outputs.graph.interface_labels** -- Add IP addresses to links in **topology** graph. Results in a cluttered image (but feel free to fix that and submit a pull request).
* **outputs.graph.colors._object_** -- Specify background color for *as*, *node*, *stub* subnet, *ibgp* or *ebgp* session.
* **outputs.graph.margins.as** -- Inner margin for autonomous system boxes.

You could specify these attributes in your topology file, in per-user topology defaults, or in system defaults ([more details](../defaults.md)). You could also specify them with `-s` parameter of **netlab create** command ([more details](../netlab/create.md)). The system defaults in *netsim-tools* release 0.9 are included below:

```
outputs:
  graph:
    interface_labels: False
    as_clusters: True
    colors:
      as: "#e8e8e8"
      node: "#ff9f01"
      stub: "#d1bfab"
      ibgp: "#613913"
      ebgp: "#b21a1a"
    margins:
      as: 16
```
