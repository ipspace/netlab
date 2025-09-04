#!/bin/bash
graph() {
  echo -n "graph $3 from $1 into $2 "
  netlab create -s graph.title="$4" -o graph$3 $1 && dot graph.dot -Tsvg -o $2
}
OPTS=${*:-bgp topo}
rm *svg
if [[ "$OPTS" == *"topo"* ]]; then
  graph topo.yml dot-topo-default.svg
  NETLAB_OUTPUTS_GRAPH_NODE__ADDRESS__LABEL=False graph topo.yml dot-topo-no-labels.svg "" "Topology graph, no labels"
  NETLAB_OUTPUTS_GRAPH_AS__CLUSTERS=False graph topo.yml dot-topo-no-clusters.svg "" "Topology graph, no AS clusters"
  NETLAB_OUTPUTS_GRAPH_INTERFACE__LABELS=True graph topo.yml dot-topo-intf-labels.svg "" "Topology graph, interface labels"
  NETLAB_OUTPUTS_GRAPH_GROUPS=[fabric,host] graph topo.yml dot-topo-groups.svg ""
fi
if [[ "$OPTS" == *"bgp"* ]]; then
  graph bgp.yml dot-bgp-default.svg :bgp
  graph bgp.yml dot-bgp-rr.svg :bgp:rr
  graph bgp.yml dot-bgp-vrf.svg :bgp:vrf
  graph bgp.yml dot-bgp-novrf.svg :bgp:novrf
  graph bgp.yml dot-bgp-evpn.svg :bgp:evpn:rr
fi
