# Link Aggregation Group (LAG) Configuration Module

This configuration module configures link bonding parameters, for LAGs between 2 devices (i.e. not MC-LAG)

(lag-platform)=
LAG is currently supported on these platforms:

| Operating system      |   lag     |  LACP off  |  LACP passive
| --------------------- | :-------: | :--------: |  :----------:
| Cumulus Linux         |    ✅     |     ✅     |      ❌
| FRR                   |    ✅     |     ✅     |      ❌

## Parameters

The following parameters can be set globally or per node/link/interface:

* **lacp**: LACP protocol interval: "fast", "slow" or "off"

  Note that 'link down' is not easily detectable in a virtual environment with veth pairs, therefore it is strongly recommended
  to enable LACP whenever possible

* **lacp_mode**: "active" or "passive"

By setting the **lag.id** parameter at the link level and defining **lag.members**, a *lag* type link is created with the given list or count of member links.

## Example

To create a LAG consisting of 2 links between 2 devices:

```
module: [ lag ]

nodes: [ r1, r2 ]

links:
- r1:
  r2:
  lag.id: 1
  lag.members: 2
```
Additional parameters such as vlan trunks, OSPF cost, etc. can be applied to such *lag* type links. 

In case additional attributes are required for the member links, the following syntax can also be used
```
links:
- r1:
  r2:
  lag:
   id: 1
   members:
   - r1:
       ifindex: 49  # Use 100G links 1/1/49 and 1/1/50
     r2:
       ifindex: 49
   - r1:
       ifindex: 50
     r2:
       ifindex: 50
```
Naturally, the links in lag.members can only use nodes associated with the lag link