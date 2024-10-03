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

* **lacp**: LACP protocol interval: "fast", "slow" or "off"
* **lacp_mode**: "active" or "passive"

The **lag.id** parameter can be set at the link or interface level; all interfaces 
with the same lag.id value form a Link Aggregation Group.

## Example

To create a LAG consisting of 2 links between 2 devices:

```
module: [ lag ]

...

links:
- r1:
  r2:
  lag.id: 1
- r1:
  r2:
  lag.id: 1
```
