(module-stp)=
# STP Configuration Module

This configuration module enables support for Spanning Tree Protocol (STP) to avoid loops by dynamically blocking ports.
Many platforms already support and enable STP by default; this module provides explicit control over those settings

(stp-platform)=
## Platform Support

The following table describes per-platform support of individual STP features:

```{features}
- title: STP
  enabled: "'stp' in stp.supported_protocols"
- title: MSTP
  enabled: "'mstp' in stp.supported_protocols"
- title: RSTP
  enabled: "'rstp' in stp.supported_protocols"
- title: Per-VLAN<br>RSTP
  enabled: "'pvrst' in stp.supported_protocols"
- title: Enable<br>per port
  enabled: stp.enable_per_port
```

**Notes:**

* Arista EOS: MSTP is enabled by default
* Arrcus ArcOS: Rapid PVST is the only flavor and is enabled by default; the only off switch is global -- there is no per-port and no per-VLAN disable
* Aruba AOS-CX: MSTP is enabled by default; STP is stated as not supported, but it is configured as MSTP (see tip below).
* Cisco IOL L2 and IOSv L2: PVRST is enabled by default. STP,RSTP are emulated with MSTP. All algorithms use the "long" stp pathcost method.
* Cumulus Linux: STP is enabled by default
* Dell OS10: PVRST is enabled by default, STP does not work on virtual networks (which are used for VXLAN)
* FRR: STP is disabled by default; STP is not supported on VLAN trunks as FRR sends BPDUs tagged, you could use Cumulus instead
* IP Infusion OcNOS: STP is disabled on individual bridge ports when you disable it on a node; the STP port type cannot be configured

```{tip}
MSTP/RSTP ports fall back to regular STP upon receiving a plain STP BPDU.
```

(module-stp-global-params)=
## Global Parameters

* **stp.protocol** (one of `stp`, `mstp`, `rstp` or `pvrst`) -- Global STP flavor to run on supporting nodes, default `stp`
* **stp.stub_port_type** (one of `normal`, `edge`, `network`, `auto` or `none`) -- Port type to configure on ports with only hosts connected, default `none` (not set). When set, this overrides any more specific **stp.port_type** value set at node or vlan level

(module-stp-params)=
## Global, Node, Link, Interface, and VLAN Parameters

* **stp.enable** (bool) -- Enable STP. Optional, default: **True**. Set this to **False** explicitly to disable STP on platforms that enable it by default. We're not responsible for the loops you might get as a result.

```{tip}
* You can set the **‌stp.enable** parameter in the **‌vlans** dictionary to enable per-VLAN STP.
* You cannot enable STP on a layer-3 interface.
```

## Node Parameters (global or per VLAN)

* **stp.protocol** (one of `stp`, `mstp`, `rstp` or `pvrst`) -- STP flavor for this node (overrides global setting)
* **stp.priority** (int 0..61440 in increments of 4096) -- STP priority for root election, by default, all nodes have equal priority 32656.  In case of equal priority, the bridge with the lowest MAC address becomes root; note that MAC addresses are assigned randomly in Netlab
* **stp.port_type** (one of `normal`, `edge`, `network` or `auto`) -- STP port type for all interfaces connected to this node

## Interface Parameters

* **stp.port_priority** (int 0..15) -- STP port priority for selecting between multiple ports; ports are blocked based on priority (lower value = higher priority). The priority is sent over the wire (4 bits) as the most significant part of the port ID; it is used by the node *receiving* it (!) to decide which port(s) to unblock. Note that on many platforms, the value that ends up in the configuration is a multiple (x16) of this attribute
* **stp.port_type** (one of `normal`, `edge`, `network` or `auto`) -- STP port type for this interface, default `normal`. Ignored if this is a stub port and **stp.stub_port_type** is set
