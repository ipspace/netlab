# Using Groups in Modules with pre_transform Hooks

*netlab* supports groups generated from BGP AS numbers to simplify setting parameters for all members of an AS. Those groups are calculated in the **module_pre_transform** hook of BGP configuration module. It's thus impossible to copy **groups._name_.node_data** structures into node data before the **pre_transform** hooks have been executed, as the group membership isn't fully evaluated until after the BGP **module_pre_transform** hook completes.

Modules that use **pre_transform** hooks to modify global- or node data structures must therefore take special precautions to cope with objects that could be defined based on **groups.node_data**. Two modules that have to deal with this are the VLAN and VRF configuration modules -- **vrfs** or **vlans** entries could be created from **groups._name_.node_data.vrfs** or **groups._name_.node_data.vlans** entries.

Both modules use the same approach:

* Create empty topology-level VRFs or VLANs from VRF/VLAN names mentioned in **vlans** or **vrfs** attributes of **groups._name_.node_data** at the beginning of **pre_transform** hook.
* Copy **id**/**vni** (for VLANs) or **rd**/**import**/**export** attributes (for VRFs) into topology-level **vlans**/**vrfs** from **node_data** entries.
* When needed, auto-generate VLAN/VNI or RD/RT data for those objects in the **pre_transform** hook
* Merge topology **vlans**/**vrfs** with node **vlans**/**vrfs** in the **post_transform** hook (any hook after the **pre_transform** hook would do).
