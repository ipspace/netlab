# Link Aggregation Group (LAG) Configuration Module

This configuration module configures link bonding parameters, for LAGs between 2 devices (i.e. not MC-LAG)

(lag-platform)=
LAG is currently supported on these platforms:

| Operating system      |   lag     |  LACP off  |  LACP passive
| --------------------- | :-------: | :--------: |  :----------:
| Cumulus Linux         |    ✅     |     ✅     |      ❌
| FRR                   |    ✅     |     ✅     |      ❌

## Parameters

The following parameters can be set globally or per node/link:

* **mode**: lag mode, one of "802.3ad" (default), "balance-xor" or "active-backup"
* **lacp**: LACP protocol interval: "fast", "slow" or "off"

  Note that 'link down' is not easily detectable in a virtual environment with veth pairs, therefore it is strongly recommended
  to enable LACP whenever possible

* **lacp_mode**: "active" or "passive"

* **ifindex**: Optional parameter to control naming of the bonding device

By setting the link type to **lag** for a link group, a *lag* type link is created with the given list of member links.

## Example

To create a LAG consisting of 2 links between devices 'r1' and 'r2':

```
module: [ lag ]

nodes: [ r1, r2 ]

links:
- group: lag1
  type: lag
  members: [ r1-r2, r1-r2 ]
```
Additional parameters such as vlan trunks, OSPF cost, etc. can be applied to such *lag* type link groups. 

In case additional attributes are required for the member links, the members can be expanded:
```
links:
- group: lag1
  type: lag
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
