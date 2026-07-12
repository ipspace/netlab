#!/bin/bash
#./run-tests.py -d $NETLAB_DEVICE -t vrf
./run-tests.py -d $NETLAB_DEVICE -t ospfv2,ospfv3 --limit 22
./run-tests.py -d $NETLAB_DEVICE -t ospfv2,ospfv3 --limit 3[01]
./run-tests.py -d $NETLAB_DEVICE -t ospfv2,ospfv3 --limit 40
./run-tests.py -d $NETLAB_DEVICE -t bgp --limit 09
./run-tests.py -d $NETLAB_DEVICE -t routing --limit 2[145]
./run-tests.py -d $NETLAB_DEVICE -t vlan --limit 52
./run-tests.py -d $NETLAB_DEVICE -t vxlan --limit 0[458]
./run-tests.py -d $NETLAB_DEVICE -t bgp_session --limit 04
./run-tests.py -d $NETLAB_DEVICE -t mpls --limit [12]
