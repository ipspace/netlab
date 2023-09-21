# Default Group Settings

This functionality adds **groups** dictionary to **defaults** (which can be read from various defaults files). The default **groups** settings will be merged with topology groups during the group initialization code:

* The **members** list in the default settings will be trimmed to contain only the valid node names (depending on the **node_auto_create** feature)
* If a group exists in the topology and the defaults, the group settings are merged. The **members** list will be taken from the topology settings (if it exists) or from the default settings.
* If a group exists in the defaults, but not in the topology, and if the **members** list is not empty, it will be copied into the topology.

Groups with empty **members** list will be removed as the last step of the group initialization process.
