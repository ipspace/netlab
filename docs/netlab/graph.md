(netlab-graph)=
# Creating Topology, BGP, or IS-IS Graphs

**netlab graph** command creates a graph description in [Graphviz](https://graphviz.org/) or [D2](https://d2lang.com/) format, or draws a graph with the help of GraphViz or D2 (which have to be installed on your system). It can use the transformed lab topology data created by the **netlab create** or **netlab up** command (usually stored in `netlab.snapshot.pickle`) or the original lab topology ([more details](netlab-graph-data-source)).

This command replicates the functionality of the **netlab create -o graph:_name_** command with a more convenient user interface. 

```{note}
_netlab_ generates the graph description files. You will have to install [Graphviz](https://graphviz.org/download/) or [D2](https://d2lang.com/tour/install) to create the actual graphs in SVG/PNG/JPEG/PDF format. You can use the **‌netlab install graph** command on a Ubuntu server to install them.
```

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Usage

```text
usage: netlab graph [-h] [-t {topology,bgp,isis}] [-i INC_LIST] [-x EXC_LIST]
                    [--title G_TITLE] [-f G_FORMAT] [-e {graphviz,d2}] [-v]
                    [-q] [--instance INSTANCE] [--snapshot [SNAPSHOT]]
                    [--topology TOPOLOGY]
                    [output]

Create a graph description in Graphviz or D2 format or draw a graph

positional arguments:
  output                Optional: Output file name

options:
  -h, --help            show this help message and exit
  -t, --type {topology,bgp,isis}
                        Graph type
  -i, --include INC_LIST
                        Links/nodes to include in the graph
  -x, --exclude EXC_LIST
                        Links/nodes to exclude from the graph
  --title G_TITLE       Graph title
  -f, --format G_FORMAT
                        Graph formatting parameters separated by commas
  -e, --engine {graphviz,d2}
                        Graphing engine
  -v, --verbose         Verbose logging (add multiple flags for increased
                        verbosity)
  -q, --quiet           Report only major errors
  --instance INSTANCE   Specify the lab instance to create a graph from
  --snapshot [SNAPSHOT]
                        Transformed topology snapshot file
  --topology TOPOLOGY   Topology file or URL

If you specify an image file as the output file (filename ending in
png/svg/jpg), netlab graph command tries to run graphviz (dot) or d2 on the
generated graph description file to create the image file you want.
```

(netlab-graph-data-source)=
## Selecting Lab Topology

The **netlab graph** command gets its data from:

* The topology file specified with the `--topology` argument
* The lab instance specified with the `-i` argument
* The snapshot file specified with the `--snapshot` argument
* The default snapshot file (`netlab.snapshot.pickle`)
* The default lab topology file (`topology.yml`)

The `netlab.snapshot.pickle` snapshot file is created when a lab is started and deleted when you shut down the lab with the `netlab down --cleanup` command.

(netlab-graph-type)=
## Selecting Graph Type and Formatting Graphs
The graph type parameter can take one of these values:

* **topology** -- draw "physical" lab topology (nodes and links)
* **bgp** -- draw BGP sessions
* **isis** -- draw IS-IS routing adjacencies

(netlab-graph-topo-format)=
These formatting parameters can be applied to a **topology** graph:

* **vlan** -- draw VLAN links in a different color. Use wider lines for VLAN trunk links.

These formatting parameters can be applied to a **bgp** graph:

* **all** -- show all lab devices in the BGP graph. By default, the BGP graphs include only lab devices running BGP
* **rr** -- draw arrows on BGP sessions to indicate peer-to-peer versus reflector-client sessions
* **vrf** -- draw VRF BGP sessions as dotted lines
* **ipv4**, **ipv6**, **vpnv4**, **vpnv6**, **6pe**, or **evpn** -- draw the BGP sessions with the specified address families
* **novrf** -- do not include VRF BGP sessions in the graph

You can also specify/overwrite the graph title with the `--title` argument.

```{tip}
* For more graph type- and graph formatting details, read the [GraphViz](outputs-graphviz) and [D2](outputs-d2) output module documentation.
* When executed with the `--instance` option, **‌netlab graph** creates the graph description file in the lab directory.
* You can use [_netlab_ environment variables](defaults-env) to change the graph appearance ([graphviz](outputs-graph-appearance), [d2](outputs-d2-graph-appearance))
```

## Generating Image Files

If you specify an image file name (for example, `graph.png`) as the output file, **netlab graph** tries to execute Graphviz (dot) or D2 after generating the graph description file to create the desired image file.

**netlab graph** recognizes `gif`, `png`, `pdf`, `svg`, `jpg`, and `jpeg` as valid image file types. You can modify the **netlab.graph.types** [system default](topo-defaults) to extend that list (assuming Graphviz/D2 recognizes the desired file types).

## Creating Graphs from a Subset of Nodes or Links

The `--include` and `--exclude` parameters can be used to create a graph from a subset of nodes or links. This is how you can use these parameters:

* You can specify one value per `--include` or `--exclude` parameter, but can specify the parameters multiple times
* The include/exclude values match node modules, link roles, or node/link **graph.class** attributes (hint: the **graph.class** attribute can be a list of values)
* If none of the specified include/exclude values match any nodes or links, **netlab graph** ignores all of the filters, emits a warning, and generates the full unfiltered graph to avoid returning an empty graph.
* If you specify just the `--include` parameter, **netlab graph** creates a graph from the nodes or links that match the include values.
* If you specify just the `--exclude` parameter, **netlab graph** removes the matching nodes/links from the topology
* When you specify both parameters, **netlab graph** removes the nodes/links matching any of the `--exclude` values unless they also match one of the `--include` values.
* After identifying the nodes/links to be removed from the lab topology, **netlab graph** removes the corresponding link attachments and node interfaces. Nodes or links that lose all connections are removed from the graph.

## Examples

* **netlab graph** creates a lab topology graph in Graphviz format
* **netlab graph graph.png** creates a lab topology graph in `graph.dot` Graphviz graph description file and executes `dot graph.dot -T png -o graph.png` to create `graph.png`.
* **netlab graph -e d2 -t bgp** creates a graph of BGP sessions in D2 format.
* **netlab graph -t bgp -f vrf** creates a graph of BGP sessions with VRF sessions shown as dashed lines ([more details](outputs-graph-bgp-parameters))
* **netlab graph --include bgp** creates a topology graph containing all nodes that run BGP.
* **netlab graph --exclude external** creates a topology graph without any inter-AS links (they have **role** set to **external**)
