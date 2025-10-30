(netlab-graph)=
# Creating Topology, BGP, or IS-IS Graphs

**netlab graph** command creates a graph description in [Graphviz](https://graphviz.org/) or [D2](https://d2lang.com/) format, or draws a graph with the help of GraphViz or D2 (which have to be installed on your system). It can use the transformed lab topology data created by the **netlab create** or **netlab up** command (usually stored in `netlab.snapshot.pickle`) or the original lab topology ([more details](netlab-graph-data-source)).

This command replicates the functionality of the **netlab create -o graph:_name_** command with a more convenient user interface. 

```{note}
_netlab_ generates the graph description files. You will have to install [Graphviz](https://graphviz.org/download/) or [D2](https://d2lang.com/tour/install) to create the actual graphs in SVG/PNG/JPEG/PDF format. You can use the **‌netlab install graph** command on a Ubuntu server to install them.
```

## Usage

```text
usage: netlab graph [-h] [-t {topology,bgp,isis}] [-f G_FORMAT] [-e {graphviz,d2}]
                    [-i INSTANCE] [--snapshot [SNAPSHOT]] [--topology TOPOLOGY]
                    [output]

Create a graph description in Graphviz or D2 format or draw a graph

positional arguments:
  output                Optional: Output file name

options:
  -h, --help            show this help message and exit
  -t, --type {topology,bgp,isis}
                        Graph type
  -f, --format G_FORMAT
                        Graph formatting parameters separated by commas
  -e, --engine {graphviz,d2}
                        Graphing engine
  -i, --instance INSTANCE
                        Specify lab instance to create a graph from
  --snapshot [SNAPSHOT]
                        Transformed topology snapshot file
  --topology TOPOLOGY   Topology file or URL

If you specify an image file as the output file (filename ending in png/svg/jpg), netlab
graph command tries to run graphviz (dot) or d2 on the generated graph description file
to create the image file you want.
```

(netlab-graph-data-source)=
The **netlab graph** command gets its data from:

* The topology file specified with the `--topology` argument
* The lab instance specified with the `-i` argument
* The snapshot file specified with the `--snapshot` argument
* The default snapshot file (`netlab.snapshot.pickle`)
* The default lab topology file (`topology.yml`)

The `netlab.snapshot.pickle` snapshot file is created when a lab is started and deleted when you shut down the lab with the `netlab down --cleanup` command.

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

```{tip}
* For more graph type- and graph formatting details, read the [GraphViz](outputs-graphviz) and [D2](outputs-d2) output module documentation.
* When executed with the `--instance` option, **‌netlab graph** creates the graph description file in the lab directory.
* You can use [_netlab_ environment variables](defaults-env) to change the graph appearance ([graphviz](outputs-graph-appearance), [d2](outputs-d2-graph-appearance))
```

## Generating Image Files

If you specify an image file name (for example, `graph.png`) as the output file, **netlab graph** tries to execute Graphviz (dot) or D2 after generating the graph description file to create the desired image file.

**netlab graph** recognizes `gif`, `png`, `pdf`, `svg`, `jpg`, and `jpeg` as valid image file types. You can modify the **netlab.graph.types** [system default](topo-defaults) to extend that list (assuming Graphviz/D2 recognizes the desired file types).

## Examples

* **netlab graph** creates a lab topology graph in Graphviz format
* **netlab graph graph.png** creates a lab topology graph in `graph.dot` Graphviz graph description file and executes `dot graph.dot -T png -o graph.png` to create `graph.png`.
* **netlab graph -e d2 -t bgp** creates a graph of BGP sessions in D2 format.
* **netlab graph -t bgp -f vrf** creates a graph of BGP sessions with VRF sessions shown as dashed lines ([more details](outputs-graph-bgp-parameters))
