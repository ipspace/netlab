# EVPN Data Model Ideas

Goals:

* Initial implementation of the EVPN module shall provide the control plane for VXLAN data plane
* Future additions might include MPLS and SRv6 data planes
* The EVPN module supports _VLAN-based Service Interface_ where every VLAN is a separate MAC VRF and _VLAN-aware Bundle Interface_ where a bunch of VLANs are part of a single MAC VRF
* EVPN module must support VLAN-over-VXLAN bridging, asymmetrical IRB, and symmetrical IRB

Data model uses existing VLAN and VRF data structures as follows:

* MAC VRF is using the VRF data structure with VLANs