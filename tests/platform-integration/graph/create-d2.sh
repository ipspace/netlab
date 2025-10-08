#!/bin/bash
OPTS=${*:-bgp topo isis}
rm *svg
if [[ "$OPTS" == *"elk"* ]]; then
  export D2_LAYOUT=elk
fi
if [[ "$OPTS" == *"topo"* ]]; then
  netlab create -o d2 topo.yml && d2 graph.d2 d2-topo-default.svg
  NETLAB_OUTPUTS_D2_NODE__ADDRESS__LABEL=False netlab create -o d2 topo.yml && d2 graph.d2 d2-topo-no-labels.svg
  NETLAB_OUTPUTS_D2_AS__CLUSTERS=False netlab create -o d2 topo.yml && d2 graph.d2 d2-topo-no-clusters.svg
  NETLAB_OUTPUTS_D2_INTERFACE__LABELS=True netlab create -o d2 topo.yml && d2 graph.d2 d2-topo-intf-labels.svg
  NETLAB_OUTPUTS_D2_GROUPS=[fabric,host] netlab create -o d2 topo.yml && d2 graph.d2 d2-topo-groups.svg
fi
if [[ "$OPTS" == *"bgp"* ]]; then
  NETLAB_GRAPH_TITLE="Default BGP graph" netlab create -o d2:bgp bgp.yml && d2 graph.d2 d2-bgp-default.svg
  NETLAB_OUTPUTS_D2_BGP_RR=False netlab create -o d2:bgp bgp.yml && d2 graph.d2 d2-bgp-no-rr.svg
  NETLAB_GRAPH_TITLE="VRF BGP sessions" netlab create -o d2:bgp:vrf bgp.yml && d2 graph.d2 d2-bgp-vrf.svg
  NETLAB_GRAPH_TITLE="BGP sessions with EVPN AF" netlab create -o d2:bgp:evpn bgp.yml && d2 graph.d2 d2-bgp-evpn.svg
fi
if [[ "$OPTS" == *"isis"* ]]; then
  NETLAB_GRAPH_TITLE="IS-IS routing" netlab create -o d2:isis isis.yml && d2 graph.d2 d2-isis.svg
fi
if [[ "$OPTS" == *"vlan"* ]]; then
  NETLAB_GRAPH_TITLE="VLAN Access and Trunk Links"  netlab create -o d2:topology:vlan vlan.yml && d2 graph.d2 d2-vlan.svg
fi
