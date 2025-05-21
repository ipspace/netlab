(example-vlan-mode)=
# Selecting the VLAN Mode

ChatGPT created the following explanation when asked about mapping VLAN design/mental models into _netlab_ **vlan.mode** parameter (the final text was merged from multiple ChatGPT responses):

---

Virtual LANs (VLANs) are used to segment Layer 2 broadcast domains within a network. The design models for VLANs typically fall into a few categories based on how traffic is forwarded and whether Layer 3 (routing) capabilities are introduced.

## Bridge Mode (Layer 2 Switching)

**Mental Model**: VLANs are used to divide a physical switch into multiple Layer 2 (L2) broadcast domains. Devices in the same VLAN can communicate directly; devices in different VLANs need a router.

**Analogy:** VLANs are like separate rooms—devices in the same room can talk freely, but to talk to another room, you need to go through the hallway (router).

**Design Model**:

* VLANs act as isolated broadcast domains.
* Devices in the same VLAN can communicate at Layer 2 without routing.
* The switch simply forwards frames based on MAC addresses.

**Use Cases**:

* Basic network segmentation (e.g., separating departments).
* Enforcing isolation without needing Layer 3 services.
* Extending Layer 2 networks across locations via VLAN trunks.

**Data Model Mapping**:

`mode = "bridge"`: Indicates the VLAN is used purely for Layer 2 switching without any IP routing associated with it.

## Layer 3 Routed VLANs

**Mental Model:** VLANs are used more like tags or identifiers for routed subnets, with no actual L2 switching behavior.

**Analogy:** VLANs are like postcodes used to route traffic—there’s no local street behavior, just an address that routes packets elsewhere.

**Design Model**:

* VLAN interfaces are routed interfaces only, with no Layer 2 bridging.
* Typically, each VLAN maps to a separate IP subnet and is connected to a routed port or subinterface.

**Use Cases**:

* Pure Layer 3 networks, where each VLAN is terminated at a router.
* Spine-leaf architectures in data centers using Layer 3 ECMP (Equal-Cost Multi-Path) routing.
* Environments that use routing protocols like OSPF/BGP between VLANs/subnets.

**Data Model Mapping**:

`mode = "route"`: Indicates the VLAN exists solely for routing—no Layer 2 forwarding occurs.

## IRB Mode (Integrated Routing and Bridging)

**Mental Model:** VLANs support both L2 and L3 functionalities—local L2 switching within the VLAN and L3 routing via an interface in the VLAN.

**Analogy:** A room (VLAN) with a door (IRB interface) leading to other rooms (other VLANs) via a hallway (router).

**Design Model**:

-   Also called **Routed Bridge Interfaces** or **Switched Virtual Interfaces (SVIs)**.
-   Allows a VLAN to have both Layer 2 bridging and Layer 3 routing on the same device.
-   The VLAN is bridged for traffic within the VLAN and routed for inter-VLAN traffic.

**Use Cases**:

-   Networks requiring communication both within and across VLANs.
-   Data centers where virtual machines or services in the same VLAN need to talk to others in different VLANs.
-   Smooth migration from Layer 2 to Layer 3.

**Data Model Mapping**:

`mode = "irb"`: Indicates that a VLAN is both bridging at Layer 2 and associated with a Layer 3 interface (IP routing is enabled on the VLAN).

## Summary Table

| VLAN Mode	| Layer	| Forwarding Behavior	| Typical Use Cases	|
|-----------|-------|---------------------|-------------------|
| `bridge`  | Layer 2	| MAC-based switching	| Basic segmentation, isolation	"bridge" |
| `irb`     | L2 + L3	| Bridge within VLAN, route between	| Mixed L2/L3, inter-VLAN routing |
| `route`   | Layer 3	| IP routing only	| Pure L3 networks, scalable DCs |
