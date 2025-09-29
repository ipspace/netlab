(outputs-graphviz)=
# Topology Graph (Graphviz) Output Module

*graph* output module create a graph description of network topology or routing protocols in [*Graphviz* DOT format](https://graphviz.org/doc/info/lang.html). You can use that description with *Graphviz* commands to create topology- or routing protocol diagrams in [numerous output formats](https://graphviz.org/docs/outputs/).

**Note**: The graph descriptions contain nodes and links, but no placement information. *Graphviz* is pretty good at figuring out how to draw the required graph, but it pays off to test out various [layout engines](https://graphviz.org/docs/layouts/) (hint: use the name of the layout engine as the [CLI command](https://graphviz.org/doc/info/command.html)) and [node ranks](outputs-graph-layout).

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Creating Graph Description File

The *graph* output module is invoked with the **[netlab graph](netlab-graph)** command or by specifying the `-o graph` parameter in the **[netlab create](netlab-create)** command. It takes an optional destination file name (default: `graph.dot`).

The `-t` parameter of the **netlab graph** command or a formatting modifier in the **netlab create** `-o` parameter can be used to specify the graph type:

* **topology** (default) -- Display inter-node links, multi-access-, and stub subnets. When the network topology contains BGP information, the graph groups nodes into autonomous systems. Alternatively, you could set **defaults.outputs.graph.groups** attribute to use topology **[groups](topo-groups)** to group graph nodes.
* **bgp** -- Include autonomous systems, BGP routers, and color-coded BGP sessions.
* **isis** -- Create a diagram of IS-IS routing, including areas, color-coded circuit types, and edge subnets (does not work with IS-IS running over VLANs)

```{tip}
The `‑f` parameter of the **netlab graph** command or a formatting modifier of the **‌netlab create** `‑o` parameter can include [BGP formatting parameters](outputs-graph-bgp-parameters). For example, `netlab graph -t bgp -f rr` draws RR-client sessions as directed arrows.
```

Use the **dot** command (or another Graphviz command) to create a graph from a graph description file. The Graphviz commands take the `-T` argument to specify the output format (for example, `png` or `svg`) and the `-o` argument to specify the output file. For example, use the following command to create `graph.png`:

```
$ dot graph.dot -T png -o graph.png
```

(outputs-graph-link-node-attributes)=
## Modifying Global, Link, and Node Attributes

You can set the graph title with **graph.title** or **defaults.graph.title** topology attribute.

You can use the **graph** link and node attributes to change the style of individual nodes or links. The following attributes are built into _netlab_[^XS]:

* **graph.color** -- line color (*color* Graphviz attribute)
* **graph.fill** -- fill color (*fillcolor* Graphviz attribute)
* **graph.width** -- line width (*penwidth* Graphviz attribute)

[^XS]: You can extend the Graphviz styling capabilities and add new **graph** attributes. See [](outputs-d2-styles) for details.

You can also use the **graph.format** parameter to specify the [Graphviz attributes](https://graphviz.org/doc/info/attrs.html) for individual nodes or links[^LFA]. For example, to change the width of a node to 2 inches, use:

```
nodes:
  spine:
    graph.format.width: 2
```

Likewise, to turn a link into a dashed line, use:

```
links:
- interfaces: [ a,b ]
  graph.format.style: dashed
```

[^LFA]: Link attributes are applied to links between nodes or to the node representing a multi-access subnet.

(outputs-graph-layout)=
## Influencing the Graph Layout

_netlab_ uses the node **graph.rank** attribute to:

1. Tell Graphviz that nodes with the same **graph.rank** should be at the same rank (vertical position) in the graph
2. Sort nodes in link definitions to ensure the graph edges are always defined as going from nodes with a lower rank to nodes with a higher rank. The order of nodes in the graph edges influences the Graphviz layout engine.

The default value of the **graph.rank** attribute is 100, allowing you to push some nodes (with rank below 100) toward the top of the graph and others (with rank above 100) toward the bottom.

You can also use the **graph.rank** on links to influence how Graphviz draws multi-access links.

Finally, the link/interface **graph.linkorder** attribute allows you to specify the node order in individual links. The default **graph.linkorder** value is 50 for interfaces and 100 for subnets (multi-access links), resulting in subnets being "below" nodes unless you change the link- or interface **graph.linkorder** value.

(outputs-graph-appearance)=
## Modifying Graph Appearance

Graphing routines use **[defaults](topo-defaults)** topology settings to modify the generated DOT file's node- or link parameters. These defaults influence how your graphs look:

* **outputs.graph.as_clusters** (default: *True*) -- use BGP AS numbers to create graph clusters
* **outputs.graph.groups** -- use the specified list of groups (or all groups when set to *True*) to create graph clusters
* **outputs.graph.interface_labels** -- Add IP addresses to links in **topology** graph. Results in a cluttered image (but feel free to fix that and submit a pull request).
* **outputs.graphs.node_address_label** (default: *True*) -- add node loopback IP addresses or IP addresses of the first interface (for hosts) to node labels.

(outputs-graph-bgp-parameters)=
These default settings modify how the BGP graphs look:

* **outputs.graph.bgp.all** (default: False) -- show all lab devices in the BGP graph. By default, the BGP graphs include only lab devices running BGP
* **outputs.graph.bgp.rr** (default: True) -- draw arrows on BGP sessions to indicate peer-to-peer versus reflector-client sessions
* **outputs.graph.bgp.vrf** (default: False) -- draw VRF BGP sessions as dotted lines
* **outputs.graph.bgp.af._af_** (default: all address families) -- when one or more **af** parameters (valid keys: **ipv4**, **ipv6**, **vpnv4**, **vpnv6**, **6pe**, **evpn**) are set to *True*, the graph is limited to BGP sessions of the specified address families.
* **outputs.graph.bgp.novrf** (default: False) -- do not include VRF BGP sessions in the graph

You can specify the above BGP parameters in the *graph format* CLI argument, for example, `netlab create -o graph:bgp:vrf` or `netlab graph -t bgp -f vrf`.

(outputs-graph-styles)=
## Graph Object Styles

Finally, you can also change the formatting of individual graph objects with the **outputs.graph.styles._object_** defaults:

| Object | Description |
|--------|-------------|
| graph  | Generic graph formatting |
| node   | Device formatting |
| edge   | Link formatting   |
| as     | Autonomous system/group container formatting |
| stub   | Subnet formatting
| title  | Graph title formatting |
| ibgp   | IBGP session formatting |
| ebgp   | IBGP session formatting |
| vrf    | BGP VRF session formatting |
| localas_ibgp | Local-AS IBGP session formatting |
| confed_ebgp  | Confederation EBGP session formatting |
| level-1 | IS-IS level-1-only link |
| level-2 | IS-IS level-2-only link |
| level-1-2 | IS-IS level-1-2 link |

Each **styles** parameter is a dictionary of *Graphviz* attributes and their values.

You could specify the graph defaults in your [topology file](defaults-topology) (where you would have to prefix them with **defaults**), in [per-user topology defaults](defaults-user-file), or with [environment variables](defaults-env) (even [more details](../defaults.md)). You could also specify them with the `-s` parameter of the **[netlab create](netlab-create)** command, yet again prefixed with **defaults** ([more details](netlab-create-set)).

To display the current Graphviz styles, use the **netlab show defaults outputs.graph.styles** command.

```{tip}
Older _netlab_ releases (prior to release 25.09) used different default settings to change a few graph parameters. You can still change those defaults, but don't use them in new projects:

* **outputs.graph.colors._object_** -- Specify background color for *as*, *node*, *stub* subnet, *ibgp* or *ebgp* session.
* **outputs.graph.margins.as** -- Inner margin for graph clusters (BGP autonomous system or groups).
```

## Sample Graphs

The lab topologies used for platform integration testing contain numerous examples of graph attributes:

* [Leaf-and-spine topology](https://github.com/ipspace/netlab/blob/master/tests/platform-integration/graph/topo.yml) used to create topology graphs and test node- and link attributes and custom formatting.
* [EVPN topology](https://github.com/ipspace/netlab/blob/master/tests/platform-integration/graph/bgp.yml) used to create BGP graphs
* [IS-IS topology](https://github.com/ipspace/netlab/blob/master/tests/platform-integration/graph/isis.yml) used to create IS-IS graphs and test node ranking

You'll find [further graph-creation tips](https://blog.ipspace.net/tag/netlab/#graph) on the ipSpace.net blog.