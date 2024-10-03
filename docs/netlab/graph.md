(netlab-graph)=
# Creating Physical or BGP Topology Graphs

**netlab graph** command creates a graph description in [Graphviz](https://graphviz.org/) or [D2](https://d2lang.com/) format from the transformed lab topology data (usually stored in `netlab.snapshot.yml`) created by **netlab create** command. It's replicating the functionality of **netlab create -o graph:_name_** command with a more convenient user interface. 

```{note}
You will have to install [Graphviz](https://graphviz.org/download/) or [D2](https://d2lang.com/tour/install) and use them to create the actual graphs in PNG/JPEG/PDF format.
```

## Usage

```text
usage: netlab graph [-h] [--snapshot [SNAPSHOT]] [-t {topology,bgp}] [-e {graphviz,d2}] [output]

Create a graph description in Graphviz or D2 format

positional arguments:
  output                Optional: Output file name

options:
  -h, --help            show this help message and exit
  --snapshot [SNAPSHOT]
                        Transformed topology snapshot file
  -t {topology,bgp}, --type {topology,bgp}
                        Graph type
  -e {graphviz,d2}, --engine {graphviz,d2}
                        Graphing engine
```

## Examples

* **netlab graph** creates lab topology graph in Graphviz format
* **netlab graph -e d2 -t bgp** creates a graph of BGP sessions in D2 format.
