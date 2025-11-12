#!/bin/bash
OPTS=${*:-bgp topo isis}
rm *svg
if [[ "$OPTS" == *"topo"* ]]; then
  netlab graph --topology topo.yml dot-topo-default.svg
  NETLAB_GRAPH_TITLE="Topology graph, no labels" \
  NETLAB_OUTPUTS_GRAPH_NODE__ADDRESS__LABEL=False netlab graph --topology topo.yml dot-topo-no-labels.svg
  NETLAB_GRAPH_TITLE="Topology graph, no AS clusters" \
  NETLAB_OUTPUTS_GRAPH_AS__CLUSTERS=False netlab graph --topology topo.yml dot-topo-no-clusters.svg
  NETLAB_GRAPH_TITLE="Topology graph, interface labels" \
  NETLAB_OUTPUTS_GRAPH_INTERFACE__LABELS=True netlab graph --topology topo.yml dot-topo-intf-labels.svg
  NETLAB_GRAPH_TITLE="Topology graph, custom groups" \
  NETLAB_OUTPUTS_GRAPH_GROUPS=[fabric,host] netlab graph --topology topo.yml dot-topo-groups.svg
fi
if [[ "$OPTS" == *"bgp"* ]]; then
  NETLAB_GRAPH_TITLE="Default BGP graph" \
  NETLAB_GROUPS_CORE_GRAPH_RANK=1 \
  netlab graph --topology bgp.yml -t bgp dot-bgp-default.svg
  NETLAB_GRAPH_TITLE="BGP graph with RR sessions" \
  netlab graph --topology bgp.yml -t bgp -f rr dot-bgp-rr.svg
  NETLAB_GRAPH_TITLE="BGP graph with VRF sessions" \
  netlab graph --topology bgp.yml -t bgp -f vrf dot-bgp-vrf.svg
  NETLAB_GRAPH_TITLE="No VRF sessions in the BGP graph" \
  netlab graph --topology bgp.yml -t bgp -f novrf dot-bgp-novrf.svg
  NETLAB_GRAPH_TITLE="EVPN BGP sessions" \
  netlab graph --topology bgp.yml -t bgp -f evpn,rr dot-bgp-evpn.svg
fi
if [[ "$OPTS" == *"isis"* ]]; then
  NETLAB_GRAPH_TITLE="IS-IS routing" \
  netlab graph --topology isis.yml -t isis dot-isis.svg
fi
if [[ "$OPTS" == *"vlan"* ]]; then
  NETLAB_GRAPH_TITLE="VLAN Access and Trunk Links" \
  netlab graph --topology vlan.yml -f vlan dot-vlan.svg
fi
