# VLAN, VRF, VXLAN, and EVPN Transformations

The VLAN, VRF, VXLAN, and EVPN configuration modules are tightly coupled and use shared **vlans** and **vrfs** data structures. This document describes the chain of events taking place in these modules during the *netlab* data transformation and how they populate the shared data structures.

The **transform_after** settings cause the hooks to be called in the VLAN -> VRF -> VXLAN -> EVPN order.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: entry
```

## init

### EVPN

* Set default **vxlan.flooding** mode to **evpn**

## pre_transform

### VLAN

Module:
* Create global VLANs based on group VLAN data
* Collect static VLAN IDs
* Validate VLAN attributes: forwarding mode, VLAN ID, link attributes, module-specific VLAN/link attributes
* Auto-assign VLAN IDs to VLANs without a valid ID
* Create VLAN access links in the lab topology from **vlans._name_.links** list
* Allocate IP prefixes to VLANs

Node:
* Merge global VLAN data with node VLAN data
* Validate VLAN attributes (see above)
* Allocate IP prefixes to node-only VLANs

Link:
* Validate link-level VLAN attribute: valid combinations of access/trunk/native VLANs, valid VLAN names in **vlan.\*** link- and interface attributes

For trunk links: create VLAN member links out of a VLAN trunk
* For every VLAN in the trunk, create a `vlan_member` link
* Process `vlan_member` link like it would be an access link

For access links:
* Set the VLAN forwarding mode (`_vlan_mode`) for every interface attached to the link (see [VLAN module documentation](../module/vlan.md) for precedence details)
* Add VLAN data to link data
* For routed VLAN links, set link VLAN mode to **route**
* For non-routed links, set link prefix based on VLAN prefix
* Disable interface addresses on bridge-only VLANs or on bridge-only interfaces

### VRF

Module:
* Create global VRFs based on group VRF data
* Normalize VRF IDs and collect static ID/RD settings
* Auto-assign VRF ID/RD and import/export RT

Node:
* Pull global VRFs that are needed by node VLANs into nodes
* Normalize VRF IDs and collect static ID/RD settings
* Auto-assign VRF ID/RD and import/export RT (based on some global AS)

### VXLAN

Node:
* Check/set flooding value

### EVPN

Module:
* Register static VRF **evpn.transit_vni**

## post_node_transform

### VXLAN

Module:
* Create default **vxlan.vlans** list (all global or node VLANs) when **vxlan.vlans** is missing
* Validate **vxlan.vlans** list in topology and nodes
* Assign VNIs to VLANs in **vxlan.vlans** list

### EVPN
* Create default **evpn.vrfs** list when missing
* Create default **evpn.vlans** list when missing
* Assign VNIs to VRFs with **evpn.transit_vni** set to *True* or string (another VRF) value
* Make sure **evpn.transport** is set for EVPN VLANs and (bundle) VRFs

Create VLAN- and VRF services:
* Assign EVPN RD/RT to EVPN-enabled VLANs and -bundles (with RT based on some global AS, not per node AS)
* Assign **evpn.evi** to EVPN-enabled VRFs

## pre_link_transform

### VLAN

Module:
* Create loopback VLAN links: for every node that has a VLAN configured but does not participate in that VLAN with a physical interface, create a fake member link with a fake interface attached to it.

## post_link_transform

### VLAN

Module:
* Copy final topology VLAN data into nodes
* Create SVI interfaces
* Map trunk VLAN names into VLAN IDs
* Rename VLAN subinterfaces (routers and routed interfaces on L3 switches)
* Remove *routed native VLAN* from trunk list
* Check for mixed (bridged+routed) trunks
* Set neighbors for SVI interfaces
* Remove VLAN member links from topology links
* Cleanup temporary VLAN attributes in links and nodes -- remove `vlan_name` from links and interfaces, `_global_merge` from VLANs and interfaces, `neighbors` from node VLANs, and `_vlan_mode` from interfaces. Also: copy interface `_vlan_mode` into interface `vlan.mode`.
* Fix VLAN-wide default gateways

### VRF

Node:
* Create node VRFs based on interface **vrf** attributes
* Merge global VRFs with node VRFs

## post_transform

### VRF

Node:
* Check RD values for VRFs used in the node
* Set **af.vpnv4** and **af.vpnv6** and VRF **af** dictionary
* Check device features (inter-VRF route leaking)
* Set **vrf.vrfidx** (used to set OSPF process ID)
* Create VRF loopbacks

### VXLAN

Module:
* Build final node **vxlan.vlans** list
* Set node VXLAN flooding domain
* Build (per-node/per-VLAN) ingress replication lists

### EVPN

Node:
* Enable EVPN address family
* Check VRF IRB setup against device features
* Copy global EVPN lists into node data (if needed)
* Trim **evpn.vlans** and **evpn.vrfs** to refer only to VLANs and VRFs present on this node
* Set **bgp.router_id:evpn.evi** RD on EVPN-enabled VLANs and VRFs
