(netlab-graph)=
# Creating Topology, BGP, or IS-IS Graphs

**netlab graph** command creates a graph description in [Graphviz](https://graphviz.org/) or [D2](https://d2lang.com/) format from the transformed lab topology data (usually stored in `netlab.snapshot.pickle`) created by **netlab create** command. 

It replicates the functionality of the **netlab create -o graph:_name_** command with a more convenient user interface. 

```{note}
_netlab_ generates the graph description files. You will have to install [Graphviz](https://graphviz.org/download/) or [D2](https://d2lang.com/tour/install) and use them to create the actual graphs in SVG/PNG/JPEG/PDF format.
```

## Usage

```text
usage: netlab graph [-h] [-t {topology,bgp,isis}] [-f G_FORMAT] [-e {graphviz,d2}]
                    [-i INSTANCE] [--snapshot [SNAPSHOT]] [output]

Create a graph description in Graphviz or D2 format

positional arguments:
  output                Optional: Output file name

options:
  -h, --help            show this help message and exit
  -t {topology,bgp,isis}, --type {topology,bgp,isis}
                        Graph type
  -f, --format G_FORMAT
                        Graph formatting parameters separated by commas
  -e {graphviz,d2}, --engine {graphviz,d2}
                        Graphing engine
  -i INSTANCE, --instance INSTANCE
                        Specify lab instance to create a graph from
  --snapshot [SNAPSHOT]
                        Transformed topology snapshot file
```

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

## Examples

* **netlab graph** creates lab topology graph in Graphviz format
* **netlab graph -e d2 -t bgp** creates a graph of BGP sessions in D2 format.
* **netlab graph -t bgp -f vrf** creates a graph of BGP sessions with VRF sessions show as dashed lines ([more details](outputs-graph-bgp-parameters))
