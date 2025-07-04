(module-stp)=
# STP Configuration Module

This configuration module enables support for Spanning Tree Protocol (STP) to avoid loops by dynamically blocking ports.
Many platforms already support and enable STP by default; this module provides explicit control over those settings

(stp-platform)=
## Platform Support

The following table describes per-platform support of individual STP features:

| Operating system   | STP | MSTP | RSTP | Per-VLAN<br>RSTP | Enable<br>per port |
| ------------------ |:---:|:---:|:---:|:---:|:---:|
| Arista EOS[^EOS]   | ✅  | ✅  | ✅  | ✅ |  ✅ |
| Aruba AOS-CX[^AOSCX] | ❗  | ✅  | ❌  | ✅ |  ✅ |
| Cumulus Linux 4.x[^CL] | ✅  |  ❌  | ✅  | ❌   |  ✅ |
| Cumulus 5.x (NVUE)[^CL] | ✅  |  ❌  | ✅  | ❌   |  ✅ |
| Dell OS10[^OS10]   | ✅  | ✅  | ✅  | ❗ |  ✅ |
| FRR[^FRR]          | ✅  |  ❌  |  ❌  |  ❌ | ❌   |

[^EOS]: MSTP is enabled by default
[^AOSCX]: MSTP is enabled by default; STP is stated as not supported, but it is configured as MSTP (see tip below).
[^CL]: STP is enabled by default
[^OS10]: PVRST is enabled by default, STP does not work on virtual networks (which are used for VXLAN)
[^FRR]: STP is disabled by default; STP is not supported on VLAN trunks as FRR sends BPDUs tagged, you could use Cumulus instead

```{tip}
MSTP/RSTP ports fall back to regular STP upon receiving a plain STP BPDU.
```

## Global Parameters

* **stp.protocol** (one of `stp`, `mstp`, `rstp` or `pvrst`) -- Global STP flavor to run on supporting nodes, default `stp`
* **stp.stub_port_type** (one of `normal`, `edge`, `network`, `auto` or `none`) -- Port type to configure on ports with only hosts connected, default `none` (not set). When set, this overrides any more specific **stp.port_type** value set at node or vlan level

## Global, Node, Link, Interface, and VLAN Parameters

* **stp.enable** (bool) -- Enable STP. Optional, default: **True**. Set this to **False** explicitly to disable STP on platforms that enable it by default. We're not responsible for the loops you might get as a result.

```{tip}
You can set the **‌stp.enable** parameter in the **‌vlans** dictionary to enable per-VLAN STP.
```

## Node Parameters (global or per VLAN)

* **stp.priority** (int 0..61440 in increments of 1024) -- STP priority for root election, by default, all nodes have equal priority 32656.  In case of equal priority, the bridge with the lowest MAC address becomes root; note that MAC addresses are assigned randomly in Netlab
* **stp.port_type** (one of `normal`, `edge`, `network` or `auto`) -- STP port type for all interfaces connected to this node

## Interface Parameters

* **stp.port_priority** (int 0..15) -- STP port priority for selecting between multiple ports; ports are blocked based on priority (lower value = higher priority). The priority is sent over the wire (4 bits) as the most significant part of the port ID; it is used by the node *receiving* it (!) to decide which port(s) to unblock. Note that on many platforms, the value that ends up in the configuration is a multiple (x16) of this attribute
* **stp.port_type** (one of `normal`, `edge`, `network` or `auto`) -- STP port type for this interface, default `normal`. Ignored if this is a stub port and **stp.stub_port_type** is set
