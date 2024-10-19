# STP Configuration Module

This configuration module enables support for Spanning Tree Protocol (STP) to avoid loops by dynamically blocking ports.
Many platforms already support and enable STP by default; this module provides explicit control over those settings

## Platform Support

The following table describes per-platform support of individual STP features:

| Operating system   | STP | Per-VLAN STP (PVRST)
| ------------------ | :-: | :------------------: |
| Cumulus Linux      | ✅  |         ❌           ! Note: STP is enabled by default, unless disabled through this module
| FRR                | ✅  |         ✅           ! Note: STP is disabled by default

## Global Parameters

* **stp.pvrst** (bool) -- Topology requires per-VLAN Rapid Spanning Tree Protocol, implies a feature check for all STP-enabled nodes

## Global, Node, Link and Interface Parameters

* **stp.enable** (bool) -- Enable STP. Optional, default: **True**.

## Node Parameters (global or per VLAN)

* **stp.priority** (int 0..61440 in increments of 1024) -- STP priority for root election, by default all nodes have equal priority 32656.  In case of equal priority, the bridge with the lowest MAC address becomes root; note that MAC addresses are assigned randomly in Netlab

## Interface Parameters

* **stp.port_priority** (int 0..255, some platforms have lower max values) -- STP port priority for selecting between multiple ports; ports are blocked based on priority (lower value = higher priority)


