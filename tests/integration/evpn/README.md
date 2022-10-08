# EVPN Integration Test Cases

This directory contains numerous EVPN integration test cases. Please use them when implementing EVPN on a new device (or changing exiting device templates).

## VXLAN Transport

VLAN-aware service:

* `vxlan-bridging.yml` -- simple bridging of VXLAN-enabled VLANs between two switches. Test the baseline EVPN/VXLAN functionality.
* `vxlan-bridging-leaf-spine.yml` -- adds a route reflector spine layer to `vxlan-bridging.yml`. Use this test case to test route reflection in EVPN address family.

VLAN-aware bundle service:

* `vxlan-vlan-bundle.yml` -- creates a VLAN bundle (using the same RT for multiple VLANs).

Symmetric IRB:

* `vxlan-symmetric-irb.yml` -- Combination of VLAN bridging and VRF with symmetric IRB. VLANs are present on a subset of switches, making RT5 prefixes mandatory for full connectivity.
* `vxlan-symmetric-irb-leaf-pairs.yml` -- Larger topology spreading the hosts across four leafs.

