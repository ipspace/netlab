# STP Configuration Module

This configuration module enables support for Spanning Tree Protocol (STP) to avoid loops by dynamically blocking ports.
Many platforms already support and enable STP by default; this module provides explicit control over those settings

## Platform Support

The following table describes per-platform support of individual STP features:

| Operating system   | STP | MSTP | RSTP | Per-VLAN (R)STP | Enable per port
| ------------------ |:---:|:---:|:---:|:---:|:---:|
| Arista EOS[^EOS]   | ✅  | ✅  | ✅  | ✅ |  ✅ |
| Cumulus Linux[^CL] | ✅  |  ❌  | ✅  | ❌   |  ✅ |
| FRR[^FRR]          | ✅  |  ❌  |  ❌  |  ✅ | ❌   |

[^EOS]: MSTP is enabled by default
[^CL]: STP is enabled by default
[^FRR]: STP is disabled by default

```{tip}
MSTP/RSTP ports fall back to regular STP upon receiving a plain STP BPDU.
```

## Global Parameters

* **stp.protocol** (one of stp, mstp, rstp or pvrst) -- Global STP flavor to run on supporting nodes, default **stp**

## Global, Node, Link, Interface, and VLAN Parameters

* **stp.enable** (bool) -- Enable STP. Optional, default: **True**. Set this to **False** explicitly to disable STP on platforms that enable it by default. We're not responsible for the loops you might get as a result.

```{tip}
You can set the **‌stp.enable** parameter in the **‌vlans** dictionary to enable per-VLAN STP.
```

## Node Parameters (global or per VLAN)

* **stp.priority** (int 0..61440 in increments of 1024) -- STP priority for root election, by default, all nodes have equal priority 32656.  In case of equal priority, the bridge with the lowest MAC address becomes root; note that MAC addresses are assigned randomly in Netlab

## Interface Parameters

* **stp.port_priority** (int 0..255, some platforms have lower max values and/or require multiples of N) -- STP port priority for selecting between multiple ports; ports are blocked based on priority (lower value = higher priority). The priority is sent over the wire (4 bits) as the most significant part of the port ID; it is used by the node *receiving* it (!) to decide which port(s) to unblock.
