# Topology Graph (graphviz) Output Module

*graph* output module create a description of network topology in [*graphviz* DOT format](https://graphviz.org/doc/info/lang.html). You can use that description with *graphviz* commands to create topology diagrams in [numerous output formats](https://graphviz.org/docs/outputs/).

**Note**: The network topology graph description contains nodes and links but no placement information. *graphviz* is pretty good at figuring out how to draw the required graph, but it pays out to test out various [layout engines](https://graphviz.org/docs/layouts/) (hint: use the name of the layout engine as the [CLI command](https://graphviz.org/doc/info/command.html)).

The *graph* output module is invoked with the **[netlab graph](netlab-graph)** command or by specifying the `-o graph` parameter in the **netlab create** command. It takes an optional destination file name (default: `graph.dot`).

A single formatting modifier can be used to specify the graph type:

* **topology** (default) -- Display inter-node links, multi-access- and stub subnets. When the network topology contains BGP information, the graph groups nodes into autonomous systems. Alternatively, you could set **defaults.outputs.graph.groups** attribute to use topology **[groups](topo-groups)** to group graph nodes.
* **bgp** -- Include autonomous systems, nodes, and BGP sessions. The formatting modifier can include [BGP formatting parameters](outputs-graph-bgp-parameters). For example, `netlab create -o graph:bgp:rr` draws RR-client sessions as directed arrows.

(outputs-graph-link-node-attributes)=
## Modifying Global, Link and Node Attributes

You can set the graph title with **graph.title** or **defaults.graph.title** topology attribute.

You can use the **graph** link and node attributes to change the style of individual nodes or links. The following attributes are built into _netlab_[^XS]:

* **graph.color** -- line color (*color* GraphViz attribute)
* **graph.fill** -- fill color (*fillcolor* GraphViz attribute)
* **graph.width** -- line width (*penwidth* GraphViz attribute)

You can also use the **graph.linkorder** link attribute to change the order of links in the D2 graph description file, which can sometimes improve the diagrams' appearance. Links with lower **graph.linkorder** values (default: 100) appear earlier in the list of links.

[^XS]: You can extend the GraphViz styling capabilities and add new **graph** attributes. See [](outputs-d2-styles) for details.

(outputs-graph-appearance)=
## Modifying Graph Appearance

Graphing routines use **[defaults](topo-defaults)** topology settings to modify the generated DOT file's node- or link parameters. These defaults influence how your graphs look:

* **outputs.graph.as_clusters** (default: *True*) -- use BGP AS numbers to create graph clusters
* **outputs.graph.groups** -- use the specified list of groups (or all groups when set to *True*) to create graph clusters
* **outputs.graph.interface_labels** -- Add IP addresses to links in **topology** graph. Results in a cluttered image (but feel free to fix that and submit a pull request).
* **outputs.graphs.node_address_label** (default: *True*) -- add node loopback IP addresses or IP addresses of the first interface (for hosts) to node labels.

(outputs-graph-bgp-parameters)=
These default settings modify how the BGP graphs look:

* **outputs.graph.bgp.rr** (default: True) -- draw arrows on BGP sessions to indicate peer-to-peer versus reflector-client sessions
* **outputs.graph.bgp.vrf** (default: False) -- draw VRF BGP sessions as dotted lines
* **outputs.graph.bgp.af._af_** (default: all address families) -- when one or more **af** parameters (valid keys: **ipv4**, **ipv6**, **vpnv4**, **vpnv6**, **6pe**, **evpn**) are set to *True*, the graph is limited to BGP sessions of the specified address families.
* **outputs.graph.bgp.novrf** (default: False) -- do not include VRF BGP sessions in the graph

You can specify the above BGP parameters in the *graph format* CLI argument.

(outputs-graph-styles)=
## Graph Object Styles

You can also change the formatting of individual graph objects with the **outputs.graph.styles._object_** defaults:

| Object | Description |
|--------|-------------|
| graph  | Generic graph formatting |
| node   | Device formatting |
| edge   | Link formatting   |
| as     | Autonomous system/group container formatting |
| stub   | Subnet formatting
| ibgp   | IBGP session formatting |
| ebgp   | IBGP session formatting |
| localas_ibgp | Local-AS IBGP session formatting |
| confed_ebgp  | Confederation EBGP session formatting |
| title  | Graph title formatting |

Each **styles** parameter is a dictionary of *Graphviz* attributes and their values (see the following printout for an example).

You can also change graph colors and margins with old-style defaults:

* **outputs.graph.colors._object_** -- Specify background color for *as*, *node*, *stub* subnet, *ibgp* or *ebgp* session.
* **outputs.graph.margins.as** -- Inner margin for graph clusters (BGP autonomous system or groups).

You could specify the graph defaults in your [topology file](defaults-topology) (where you would have to prefix them with **defaults**), in [per-user topology defaults](defaults-user-file), or with [environment variables](defaults-env) (even [more details](../defaults.md)). You could also specify them with the `-s` parameter of the **[netlab create](netlab-create)** command, yet again prefixed with **defaults** ([more details](netlab-create-set)).

The system defaults in *netlab* release 25.09 are included below; you can always inspect them with **netlab show defaults outputs.graph**

```
% netlab show defaults outputs.graph

netlab default settings within the outputs.graph subtree
=============================================================================

as_clusters: true
attributes:
  link:
    _keys:
      linkorder:
        max_value: 200
        min_value: 1
        type: int
      type:
        type: str
        valid_values:
        - lan
    type: dict
  shared:
  - linkorder
interface_labels: false
node_address_label: true
styles:
  as:
    bgcolor: '#e8e8e8'
    color: '#c0c0c0'
    fontname: Verdana
    margin: 16
  ebgp:
    color: '#b21a1a'
    penwidth: 2
  edge:
    fontname: Verdana
    labeldistance: 1.5
    labelfontsize: 8
  graph:
    bgcolor: transparent
    nodesep: 0.5
    ranksep: 1
  ibgp:
    color: '#613913'
    penwidth: 2
  node:
    bgcolor: '#ff9f01'
    fillcolor: '#ff9f01'
    fontname: Verdana
    margin: 0.3,0.1
    shape: box
    style: rounded,filled
  stub:
    bgcolor: '#d1bfab'
    fillcolor: '#d1bfab'
    fontsize: 11
    margin: 0.3,0.1
```
