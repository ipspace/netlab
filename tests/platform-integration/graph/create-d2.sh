#!/bin/bash
OPTS=${*:-bgp topo isis}
rm *svg
if [[ "$OPTS" == *"elk"* ]]; then
  export D2_LAYOUT=elk
fi
if [[ "$OPTS" == *"topo"* ]]; then
  netlab graph --topology topo.yml d2-topo-default.svg
  NETLAB_OUTPUTS_D2_NODE__ADDRESS__LABEL=False netlab graph -e d2 --topology topo.yml d2-topo-no-labels.svg
  NETLAB_OUTPUTS_D2_AS__CLUSTERS=False netlab graph -e d2 --topology topo.yml d2-topo-no-clusters.svg
  NETLAB_OUTPUTS_D2_INTERFACE__LABELS=True netlab graph -e d2 --topology topo.yml d2-topo-intf-labels.svg
  NETLAB_OUTPUTS_D2_GROUPS=[fabric,host] netlab graph -e d2 --topology topo.yml d2-topo-groups.svg
fi
if [[ "$OPTS" == *"bgp"* ]]; then
  NETLAB_GRAPH_TITLE="Default BGP graph" netlab graph -e d2 --topology bgp.yml -t bgp d2-bgp-default.svg
  NETLAB_OUTPUTS_D2_BGP_RR=False netlab graph -e d2 --topology bgp.yml -t bgp d2-bgp-no-rr.svg
  NETLAB_GRAPH_TITLE="VRF BGP sessions" netlab graph -e d2 --topology bgp.yml -t bgp -f vrf d2-bgp-vrf.svg
  NETLAB_GRAPH_TITLE="BGP sessions with EVPN AF" netlab graph -e d2 --topology bgp.yml -t bgp -f evpn d2-bgp-evpn.svg
fi
if [[ "$OPTS" == *"isis"* ]]; then
  NETLAB_GRAPH_TITLE="IS-IS routing" netlab graph -e d2 --topology isis.yml -t isis d2-isis.svg
fi
if [[ "$OPTS" == *"vlan"* ]]; then
  NETLAB_GRAPH_TITLE="VLAN Access and Trunk Links" netlab graph -e d2 -f vlan --topology vlan.yml d2-vlan.svg
fi
