(module-lag)=
# Link Aggregation Group (LAG) Configuration Module

This configuration module configures a link aggregation group (LAG) between a pair of devices, including Multi-Chassis (MLAG)

(lag-platform)=
LAG is currently supported on these platforms:

| Operating system      | LACP | Static | Passive<br>LACP | MLAG
| --------------------- |:--:|:--:|:--:|:---:|
| Arista EOS [❗](caveats-eos) | ✅ | ✅ | ✅ |
| Cumulus Linux 4.x     | ✅ | ✅ | ❌  |
| Cumulus 5.x (NVUE)    | ✅ | ✅ | ❌  |
| FRR                   | ✅ | ✅ | ❌  |

## Parameters

The following parameters can be set globally, per node or per LAG link:

* **lag.mode**: lag mode, one of **802.3ad** (IEEE LAG standard with LACP, default value), **balance-xor** (Linux non-LACP bonding mode) or **active-backup**
* **lag.lacp**: LACP protocol interval: **fast** (1-second LACP timer, default value), **slow** (30-second LACP timer) or **off** (LACP is disabled).

```{tip}
The  _link down_ condition is not easily detectable in a virtual environment. You should always use LACP.
```

* **lag.lacp_mode**: **active** (default) or **passive** (only one of the nodes can be passive)

The following parameters can be set on individual links:

* **lag.members**: Mandatory list of links that form the LAG. It uses the [same format as the topology **links** list](link-formats).
* **lag.ifindex**: Optional parameter that controls the naming of the LAG (bonding, port-channel) interface.
* **lag.mlag**: Optional Boolean or dict with peer link parameters; see [below](mlag)

This configuration module creates a virtual link with the link type set to **lag** between the **lag.members** and appends the links described in the **lag.members** list to the topology **links** list.

## Example

The following example creates a LAG consisting of 2 links between r1 and r2:

```
module: [ lag ]

nodes: [ r1, r2 ]

links:
- lag.members: [ r1-r2, r1-r2 ]
```

You can specify any link parameter on the *lag* link.

If you require additional physical interface attributes on individual member links (or interfaces), use the dictionary link format in the **lag.members** list. The following example sets **ifindex** on every Ethernet interface that is part of the LAG to [change the Ethernet interface name](links-ifname).

```
links:
- lag.members:
  - r1:
     ifindex: 49  # Use 100G links 1/1/49 and 1/1/50
    r2:
     ifindex: 49
  - r1:
     ifindex: 50
    r2:
     ifindex: 50
```

(mlag)=
## Multi-chassis Link Aggregation (MLAG)

For platforms that support it, link level redundancy can be provided by creating multiple links to different switches. The switches have an internal *peer link* to synchronize state related to the link aggregation, allowing them to present a single consistent network interface to the connected system.

MLAG related parameters:
* **lag.mlag**: Boolean flag set on *lag* links that form a 1:M multi-chassis lag
* **lag.mlag.peergroup**: Used on peerlink to configure the group ID for the set - typically pair - of switches providing the MLAG

A simple example:
```
groups:
 _auto_create: True
 switches:
  members: [s1,s2]
  device: dellos10
 hosts:
  members: [h1,h2]
  device: frr        # 'linux' does not support the lag module yet

links:
- lag:
   members: [h1-s1,h1-s2]
   mlag: True
- lag:
   members: [h1-s1,h1-s2]
   mlag: True

# Inter-switch peer link(s) for MLAG sync
- lag:
   members: [s1-s2]  # Note that multiple physical links are allowed here
   mlag.peergroup: 1 # (also) used to derive a unique MAC address for this group of MLAG peers