#!/bin/bash
OPTS=${*:-bgp topo isis}
rm *svg
if [[ "$OPTS" == *"elk"* ]]; then
  export D2_LAYOUT=elk
fi
if [[ "$OPTS" == *"topo"* ]]; then
  netlab graph --title "Default topology graph" -e d2 --topology topo.yml d2-topo-default.svg
  NETLAB_OUTPUTS_D2_NODE__ADDRESS__LABEL=False \
    netlab graph --title "No node loopback labels" -e d2 --topology topo.yml d2-topo-no-labels.svg
  NETLAB_OUTPUTS_D2_AS__CLUSTERS=False \
    netlab graph --title "No clusters" -e d2 --topology topo.yml d2-topo-no-clusters.svg
  NETLAB_OUTPUTS_D2_INTERFACE__LABELS=True \
    netlab graph --title "Interface labels" -e d2 --topology topo.yml d2-topo-intf-labels.svg
  NETLAB_OUTPUTS_D2_GROUPS=[fabric,host] \
    netlab graph --title "Custom groups" -e d2 --topology topo.yml d2-topo-groups.svg
fi
if [[ "$OPTS" == *"bgp"* ]]; then
  netlab graph --title "Default BGP graph" -e d2 --topology bgp.yml -t bgp d2-bgp-default.svg
  NETLAB_OUTPUTS_D2_BGP_RR=False \
    netlab graph --title "No RR sessions" -e d2 --topology bgp.yml -t bgp d2-bgp-no-rr.svg
  netlab graph --title "VRF BGP sessions" -e d2 --topology bgp.yml -t bgp -f vrf d2-bgp-vrf.svg
  netlab graph --title "BGP sessions with EVPN AF" -e d2 --topology bgp.yml -t bgp -f evpn d2-bgp-evpn.svg
fi
if [[ "$OPTS" == *"isis"* ]]; then
  netlab graph --title "IS-IS routing" -e d2 --topology isis.yml -t isis d2-isis.svg
fi
if [[ "$OPTS" == *"vlan"* ]]; then
  netlab graph --title "VLAN Access and Trunk Links" -e d2 -f vlan --topology vlan.yml d2-vlan.svg
fi
