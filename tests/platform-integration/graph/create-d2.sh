#!/bin/bash
OPTS=${*:-bgp topo}
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
  netlab create -o d2:bgp bgp.yml && d2 graph.d2 d2-bgp-default.svg
  NETLAB_OUTPUTS_D2_BGP_RR=False netlab create -o d2:bgp bgp.yml && d2 graph.d2 d2-bgp-no-rr.svg
  netlab create -o d2:bgp:vrf bgp.yml && d2 graph.d2 d2-bgp-vrf.svg
  netlab create -o d2:bgp:evpn bgp.yml && d2 graph.d2 d2-bgp-evpn.svg
fi
