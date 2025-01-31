# Topology Graph (graphviz) Output Module

*graph* output module create a description of network topology in [*graphviz* DOT format](https://graphviz.org/doc/info/lang.html). You can use that description with *graphviz* commands to create topology diagrams in [numerous output formats](https://graphviz.org/docs/outputs/).

**Note**: The network topology graph description contains nodes and links but no placement information. *graphviz* is pretty good at figuring out how to draw the required graph, but it pays out to test out various [layout engines](https://graphviz.org/docs/layouts/) (hint: use the name of the layout engine as the [CLI command](https://graphviz.org/doc/info/command.html)).

The *graph* output module is invoked with the **[netlab graph](netlab-graph)** command or by specifying the `-o graph` parameter in the **netlab create** command. It takes an optional destination file name (default: `graph.dot`).

A single formatting modifier can be used to specify the graph type:

* **topology** (default) -- Display inter-node links, multi-access- and stub subnets. When the network topology contains BGP information, the graph groups nodes into autonomous systems. Alternatively, you could set **defaults.outputs.graph.groups** attribute to use topology **[groups](topo-groups)** to group graph nodes.
* **bgp** -- Include autonomous systems, nodes, and BGP sessions. With the **rr** option (specified with `netlab create -o graph:bgp:rr`), RR-client sessions are drawn as directed arrows.

## Modifying Graph Attributes

Graphing routines use **[default](topo-defaults)** topology settings to modify the generated DOT file's node- or link parameters. You can change these defaults.

* **outputs.graph.interface_labels** -- Add IP addresses to links in **topology** graph. Results in a cluttered image (but feel free to fix that and submit a pull request).
* **outputs.graph.colors._object_** -- Specify background color for *as*, *node*, *stub* subnet, *ibgp* or *ebgp* session.
* **outputs.graph.margins.as** -- Inner margin for graph clusters (BGP autonomous system or groups).
* **outputs.graph.groups** -- use the specified list of groups (or all groups when set to *True*) to create graph clusters
* **outputs.graphs.node_address_labels** -- add node loopback IP addresses or IP addresses of the first interface (for hosts) to node labels.

You could specify these attributes in your [topology file](defaults-topology) (where you would have to prefix them with **defaults**), in [per-user topology defaults](defaults-user-file), or with [environment variables](defaults-env) (even [more details](../defaults.md)). You could also specify them with the `-s` parameter of the **[netlab create](netlab-create)** command, yet again prefixed with **defaults** ([more details](netlab-create-set)).

The system defaults in *netlab* release 1.9.1 are included below; you can always inspect them with **netlab show defaults outputs.graph**

```
outputs:
  graph:
    interface_labels: False
    node_address_label: True
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
