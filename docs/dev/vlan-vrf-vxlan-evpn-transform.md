# VLAN, VRF, VXLAN, and EVPN Transformations

The VLAN, VRF, VXLAN, and EVPN configuration modules are tightly coupled and use shared **vlans** and **vrfs** data structures. This document describes the chain of events taking place in these modules during the *netlab* data transformation and how they populate the shared data structures.

The **transform_after** settings cause the hooks to be called in the VLAN -> VRF -> VXLAN -> EVPN order.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: entry
```

## pre_validate (future)

* VLAN module ensures the **vlans** dictionaries (global + nodes) has no *None* values and sensible names
* VRF module ensures the **vrfs** dictionaries (global + nodes) has no *None* values and sensible names

The pre_validate hooks are called based on topology attributes, not based on **module** settings.

## init

### EVPN

* Set default **vxlan.flooding** mode to **evpn**

## pre_transform

### VLAN

Module:
* Create global VLANs based on group VLAN data
* Collect static VLAN IDs
* Validate VLAN attributes: forwarding mode, VLAN ID
* Auto-assign VLAN IDs to VLANs without a valid ID
* Allocate IP prefixes to VLANs

Node:
* Merge global VLAN data with node VLAN data

Link:
* Validate link-level VLAN attribute: valid combinations of access/trunk/native VLANs, valid VLAN names in **vlan.\*** link- and interface attributes
* Create VLAN member links out of a VLAN trunk
* Deal with odd bits-and-pieces like routed-only VLANs or disabled interface addresses on bridge-only VLANs

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
* Assign EVPN RD/RT to EVPN-enabled VLANs and -bundles (with RT based on some global AS, not per node AS)

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
* Cleanup temporary VLAN attributes in links and nodes
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
* Create VLAN-based service (from VLANs)
* Create VLAN bundles (from VLANs in VRFs)
* Create symmetric IRB (from VRFs)
