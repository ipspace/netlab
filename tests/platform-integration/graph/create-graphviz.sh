#!/bin/bash
graph() {
  netlab create -o graph$3 $1 && dot graph.dot -Tsvg -o $2
}
OPTS=${*:-bgp topo}
rm *svg
if [[ "$OPTS" == *"topo"* ]]; then
  graph topo.yml dot-topo-default.svg
  NETLAB_OUTPUTS_GRAPH_NODE__ADDRESS__LABEL=False graph topo.yml dot-topo-no-labels.svg
  NETLAB_OUTPUTS_GRAPH_AS__CLUSTERS=False graph topo.yml dot-topo-no-clusters.svg
  NETLAB_OUTPUTS_GRAPH_INTERFACE__LABELS=True graph topo.yml dot-topo-intf-labels.svg
  NETLAB_OUTPUTS_GRAPH_GROUPS=[fabric,host] graph topo.yml dot-topo-groups.svg
fi
if [[ "$OPTS" == *"bgp"* ]]; then
  graph bgp.yml dot-bgp-default.svg :bgp
  NETLAB_OUTPUTS_GRAPH_RR__SESSIONS=True graph bgp.yml dot-bgp-rr.svg :bgp
fi
