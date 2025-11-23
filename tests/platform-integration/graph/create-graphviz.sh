#!/bin/bash
OPTS=${*:-bgp topo isis}
rm *svg
if [[ "$OPTS" == *"topo"* ]]; then
  netlab graph --title "Default topology graph" --topology topo.yml dot-topo-default.svg
  NETLAB_OUTPUTS_GRAPH_NODE__ADDRESS__LABEL=False \
    netlab graph --title "Topology graph, no labels" --topology topo.yml dot-topo-no-labels.svg
  NETLAB_OUTPUTS_GRAPH_AS__CLUSTERS=False \
    netlab graph --title "Topology graph, no AS clusters" --topology topo.yml dot-topo-no-clusters.svg
  NETLAB_OUTPUTS_GRAPH_INTERFACE__LABELS=True \
    netlab graph --title "Topology graph, interface labels" --topology topo.yml dot-topo-intf-labels.svg
  NETLAB_OUTPUTS_GRAPH_GROUPS=[fabric,host] \
    netlab graph --title "Topology graph, custom groups" --topology topo.yml dot-topo-groups.svg
fi
if [[ "$OPTS" == *"bgp"* ]]; then
  NETLAB_GROUPS_CORE_GRAPH_RANK=1 \
    netlab graph --title "Default BGP graph" --topology bgp.yml -t bgp dot-bgp-default.svg
  netlab graph --title "BGP graph with RR sessions" --topology bgp.yml -t bgp -f rr dot-bgp-rr.svg
  netlab graph --title "BGP graph with VRF sessions" --topology bgp.yml -t bgp -f vrf dot-bgp-vrf.svg
  netlab graph --title "No VRF sessions in the BGP graph" --topology bgp.yml -t bgp -f novrf dot-bgp-novrf.svg
  netlab graph --title "EVPN BGP sessions" --topology bgp.yml -t bgp -f evpn,rr dot-bgp-evpn.svg
fi
if [[ "$OPTS" == *"isis"* ]]; then
  netlab graph --title "IS-IS routing" --topology isis.yml -t isis dot-isis.svg
fi
if [[ "$OPTS" == *"vlan"* ]]; then
  netlab graph --title "VLAN Access and Trunk Links" --topology vlan.yml -f vlan dot-vlan.svg
fi
