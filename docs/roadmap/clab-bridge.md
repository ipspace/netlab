# Bridge Nodes in Pure Containerlab Topologies

One of the ideas discussed in #3421 was to build a multi-access network in a pure **clab** topology with a Linux container used as a node with **role: bridge**:

```
provider: clab

nodes:
  r1:
    device: frr
  r2:
    device: frr
  br:
    device: linux
    role: bridge

links:
- interfaces: [ r1, r2 ]
  bridge: br
```

This approach is attractive because it keeps the whole forwarding path inside the lab topology. The bridge becomes a visible node that can be configured, inspected, or used in validation tests, and it avoids host-level Linux bridge operations.

## What *netlab* Would Actually Build

The **bridge** link attribute does not create a shared containerlab LAN segment. The original multi-access link is expanded into a set of point-to-point links toward the bridge node, and *netlab* creates a separate internal bridge/VLAN instance on that node for every such segment.

That implementation has a few important consequences:

* The bridge node becomes an extra forwarding hop and a single failure domain for the whole segment.
* Every bridge-based multi-access segment consumes one internal VLAN ID on the bridge node.
* The bridge node is no longer a transparent implementation detail; its capabilities and quirks affect the lab behavior.

## Drawbacks and Caveats

### It is best suited for simple LANs

This mechanism is a good fit for small bridged segments and for failure-injection scenarios described in [](example-bridge). It is not a good foundation for complex layer-2 fabrics.

In particular:

* a bridge container can become a throughput bottleneck in larger labs;
* the whole segment depends on a single container namespace and its Linux bridge state;
* operational behavior is tied to the bridge image and its tooling, not just to containerlab.

### Link attributes are intentionally limited

The transformed link is not a full-featured replacement for a normal multi-access link. Today, only a small set of physical attributes makes sense on a bridge-implemented segment (**bandwidth**, **mtu**, **stp**).

That means this feature should be treated as a simple forwarding construct, not as a general-purpose substitute for all link types.

### The middle box matters

A host Linux bridge created directly by the provider is mostly invisible. A Linux container used as a bridge node is not:

* it must boot and be configured;
* its failure drops the whole segment;
* STP and forwarding behavior come from the Linux bridge implementation inside that container;
* troubleshooting moves from "inspect the provider bridge" to "inspect the bridge node."

That tradeoff is often acceptable when the goal is to make the segment easier to manipulate from *netlab* tests, but it is still a tradeoff.

## VLAN Caveats

VLANs are the biggest caveat of this idea.

### You cannot use the multi-access link itself as a *netlab* VLAN link

The current bridge-link transformation rejects link-level **vlan** attributes on a link using **bridge: _node_**. In other words, you cannot use this:

```
links:
- interfaces: [ r1, r2, r3 ]
  bridge: br
  vlan.trunk: [ red, blue ]
```

The reason is simple: the multi-access link is rewritten into point-to-point links, and the bridge node uses an internal bridging construct to glue those links together. That works well for "put these nodes into the same LAN" but not for "this LAN segment is itself a VLAN-aware switching construct managed by the VLAN module."

### Tagged traffic might pass, but the bridge is not modeled as a VLAN-aware switch

A Linux bridge used as a bridge node will usually forward tagged Ethernet frames just fine. That could be good enough when you only want to transport an 802.1Q trunk across the segment.

However, that is not the same as having a VLAN-aware bridge in the middle:

* *netlab* cannot model **allowed VLAN** or **native VLAN** behavior on that multi-access link;
* the bridge node cannot enforce per-VLAN filtering in a meaningful, portable way;
* you do not get per-VLAN operational semantics on the middle box (for example, selective VLAN shutdown or per-VLAN STP behavior);
* all carried VLANs share the same underlying bridge instance and the same failure domain.

### Native VLAN and mixed tagged/untagged traffic are especially slippery

Once the bridge node stops being a VLAN-aware switch and becomes a transparent Linux bridge, "native VLAN" stops meaning "the middle switch understands which VLAN is untagged on this port." It effectively becomes "some endpoints send untagged frames and others send tagged frames across the same bridged segment."

That might be good enough for a raw packet transport experiment, but it is not a great model of a real access/trunk switch.

### Per-VLAN STP behavior is not represented

The bridge-node implementation creates one internal bridge domain per multi-access segment, not one forwarding instance per carried customer VLAN. Even if the endpoints run multiple VLANs across the segment, the middle Linux bridge still sees one underlying bridge.

That makes this design a poor fit for experiments where STP, filtering, or failure behavior must differ between VLANs.

## Implementation Guidelines

The least risky way to implement this feature is to **avoid implementing a new feature at all**. Instead, we should treat it as a supported usage pattern of the existing **bridge** link attribute with a Linux bridge node in a **clab** topology.

That approach aligns well with the caveats listed above:

* we already have the right data model;
* we should preserve the "simple LAN only" semantics;
* we should not try to make the middle Linux bridge look like a full VLAN-aware switch.

That is still the right answer for the **simple untagged LAN** case.

However, the actual long-term goal is broader: we want to use a bridge node in scenarios where **VLAN trunks run across the multi-access segment**, while the Linux bridge in the middle behaves like a host bridge and stays as transparent as possible.

That goal needs a second implementation path.

### Keep the current data model

The current user-facing syntax is already good enough:

```
links:
- interfaces: [ r1, r2, r3 ]
  bridge: br
```

We should not introduce a new link type, a new provider feature, or bridge-node-specific VLAN semantics. The existing **bridge** attribute already expresses the desired intent: "implement this multi-access segment with a bridge node instead of a provider bridge."

### Reuse the current transformation code for simple LANs

The existing bridge-role transformation already does most of the required work:

* it detects a multi-access link with **bridge: _node_**;
* it expands that link into point-to-point links toward the bridge node;
* it allocates an internal VLAN/bridge instance on the bridge node;
* it keeps the implementation isolated from provider-specific multi-access logic.

That means the core implementation should continue to live in `netsim/roles/bridge.py`. Minimal-impact implementation means **do not move this logic into the clab provider code** unless we discover a provider-specific problem that cannot be solved elsewhere.

### Add a second path for transparent trunk transport

The current implementation is based on an internal VLAN allocated on the bridge node. That is fine for a simple bridged LAN, but it is the wrong abstraction for a bridge node that should transparently carry customer VLAN tags.

To reach the actual goal, we need to stop treating the bridge-backed multi-access segment as "a VLAN on the bridge node" and start treating it as "a software bridge domain implemented by the bridge node."

The crucial design point is this:

* the **edge nodes** should keep the normal *netlab* VLAN semantics;
* the **bridge node** should not participate in customer VLAN semantics at all;
* the **middle Linux bridge** should simply forward Ethernet frames between member ports, tagged or untagged, the same way a host bridge would.

### Keep provider changes to a minimum

Ideally, no provider-side topology transformation should be needed.

From the implementation point of view, a pure **clab** topology with a Linux bridge node should look exactly like any other topology that contains:

* a Linux container with **role: bridge**;
* point-to-point container links between that node and the attached endpoints;
* Linux bridge configuration generated by the existing VLAN templates.

The relevant device and template support already exists in the Linux **clab** device definition and VLAN configuration templates. If any changes are needed, they should be limited to small fixes in Linux container configuration, not to a redesign of containerlab link handling.

For the trunk-carrying scenario, the provider still should not need to know anything about VLANs. It only needs a set of point-to-point links toward the bridge node once the topology transformation is complete.

### Preserve the logical shared link through VLAN processing

The current code expands a `bridge: br` multi-access link too early. That works for simple LANs, but it breaks the VLAN model because the VLAN module no longer sees the original shared segment.

For transparent trunk transport, the original multi-access link has to stay intact long enough for the VLAN module to do its normal work:

* validate link-level `vlan.access`, `vlan.native`, and `vlan.trunk` attributes;
* copy VLAN attributes to the edge-node interfaces;
* build native VLAN and trunk VLAN lists;
* perform all the existing mixed-trunk and native-VLAN validation on the **real endpoints** of the LAN.

Only **after** that processing should *netlab* materialize the bridge node and rewrite the logical multi-access segment into point-to-point links.

In practice, that means we need to split the current `expand_multiaccess_links()` logic into two parts:

* **early/simple expansion** for the existing simple-LAN behavior;
* **late transparent expansion** for links that carry VLAN semantics across a bridge node.

### The bridge node must be outside the customer VLAN model

The bridge node should not appear as a trunk participant in the VLAN module. If it does, the VLAN module will quite reasonably try to configure trunk/native/access semantics on that node, which is not what we want.

Instead, the bridge node needs its own internal representation of a software bridge domain, separate from `node.vlans`.

That bridge-domain data structure should include at least:

* a unique internal bridge-domain name;
* the original link name or link index;
* the list of member interfaces on the bridge node;
* physical attributes that matter to the software bridge (`mtu`, `stp`);
* a flag describing the intended forwarding behavior (for example, `transparent: True`).

The important detail is that this internal object does **not** represent customer VLAN 10/20/30. It represents "the Linux bridge instance that glues these ports together."

### Linux bridge configuration must emulate a host bridge

For the target use case, the Linux bridge inside the bridge node should be configured like a plain host bridge, not like a VLAN-aware switch:

* create one Linux bridge per bridge-backed multi-access segment;
* enslave all member interfaces to that bridge;
* keep `vlan_filtering=0` so tagged frames pass transparently;
* avoid bridge VLAN membership configuration;
* avoid creating customer-VLAN subinterfaces on the bridge node;
* optionally disable features that make the bridge less transparent, such as bridge netfilter hooks or multicast snooping, if that proves necessary.

That behavior matches the user's mental model: the bridge node should behave like the host bridge that containerlab would have used, only moved into a Linux container namespace.

### STP should be treated as "single Linux bridge STP"

If STP is enabled on the bridge-backed segment, the Linux bridge should run its normal bridge STP behavior on the software bridge instance.

That is still different from per-VLAN STP on a real switch, but it is consistent with the transparency goal: the bridge node participates as a bridge, not as a VLAN-aware switch. The documentation should state clearly that this provides one bridge-level STP instance, not per-VLAN spanning tree behavior.

### Required code changes

If we want the **simple LAN** scenario, the required changes are small and focused.

If we want the **transparent trunk** scenario, the implementation is still contained, but it is no longer trivial. The required changes are:

1. **Documentation**

   Expand the user-facing documentation in:

   * `docs/node/roles.md`
   * `docs/example/bridge.md`
   * `docs/caveats.md` or this roadmap document

   The documentation should explicitly say that:

   * the feature is suitable for simple LAN segments;
   * there are two implementation modes: simple bridge-LAN and transparent trunk transport;
   * transparent trunk transport keeps VLAN semantics on the edge nodes and uses a plain Linux bridge in the middle;
   * the bridge node is not modeled as a VLAN-aware switch even when it carries tagged traffic.

2. **Bridge transformation changes (`netsim/roles/bridge.py`)**

   We need to split bridge-backed multi-access link handling into two paths:

   * retain the current behavior for simple non-VLAN segments;
   * add a transparent-link path for links that carry `vlan.*` attributes across the bridge node.

   The transparent-link path should:

   * keep the original multi-access link intact during VLAN processing;
   * create late bridge-node interfaces and point-to-point links after VLAN processing;
   * build bridge-domain data for the bridge node without allocating customer-facing internal VLANs.

   In other words, `netsim/roles/bridge.py` remains the orchestration point, but it can no longer rely on "internal VLAN on the bridge node" as the only implementation strategy.

3. **VLAN pipeline integration (`netsim/modules/vlan.py` and transform order)**

   The VLAN module has to see the logical multi-access link **before** the bridge node is inserted into the topology.

   We therefore need one of these two approaches:

   * add a late bridge-expansion hook that runs after VLAN processing, or
   * teach the VLAN module to operate on the original logical link while ignoring the future bridge-node attachment.

   The first option is cleaner. It keeps the current VLAN logic focused on the real endpoints and avoids special cases in trunk/native VLAN validation.

   The concrete implementation work includes:

   * preserving the original shared-link data long enough for VLAN processing;
   * ensuring edge-node interfaces keep the VLAN data derived from that shared link;
   * rebuilding neighbor/interface metadata after the logical link is materialized into point-to-point links.

4. **Linux bridge-node configuration**

   We need new Linux bridge-node configuration logic that is separate from the current VLAN-as-bridge implementation.

   That probably means:

   * adding a dedicated internal bridge-domain representation in node data;
   * extending the Linux **clab** templates, or adding a dedicated template, to create plain Linux bridge instances;
   * enslaving member ports to those bridge instances without configuring VLAN membership.

   Reusing the existing VLAN template machinery is possible only if it can express "create a bridge and attach ports, but do not assign customer VLAN semantics to those ports." If that becomes awkward, a separate template path is the better option.

5. **Validation and error reporting**

   The current bridge-link transformation already rejects many unsupported combinations. We should add or improve explicit validation for the combinations most likely to confuse users, especially:

   * allowing `bridge: br` combined with link-level `vlan.*` attributes only when the bridge node can implement transparent bridging;
   * rejecting device types that claim `role: bridge` but cannot provide the required transparent Linux-bridge behavior;
   * rejecting features that still cannot be made transparent enough on the middle node.

   The goal is to fail early when the user's intent cannot be implemented faithfully enough.

6. **Tests**

   We should add focused tests proving the intended supported behavior:

   * a simple pure-**clab** topology with `device: linux` and `role: bridge`;
   * a test showing that multiple bridge-backed LAN segments can share the same bridge node;
   * a topology in which two or more devices use a VLAN trunk across a bridge-backed multi-access segment;
   * a topology with a native VLAN on that segment;
   * negative tests proving that unsupported "bridge node as VLAN-aware switch" scenarios are still rejected.

   These tests belong in three places:

   * transformation tests for link expansion order and internal data structures;
   * error tests for unsupported combinations;
   * at least one integration test proving that tagged frames cross the Linux bridge node unchanged.

### Changes that should be avoided

To keep the impact low, we should explicitly avoid:

* new bridge-specific provider logic in `netsim/providers/clab.py`;
* pretending that the middle Linux bridge is a VLAN-aware switch;
* modeling allowed/native VLAN semantics on the middle Linux bridge itself;
* special-case behavior that differs between Linux bridge nodes and other bridge-capable devices.

Those changes would turn a transparent software bridge into a pseudo-switch implementation, which is exactly what we want to avoid.

### If we ever want VLAN-aware behavior

If the long-term goal becomes "run a realistic trunk across a bridge-backed multi-access network and make the middle node understand VLAN semantics," then we should treat that as a separate feature.

That feature would require more than incremental changes:

* extending bridge-link transformation to understand link-level VLAN attributes;
* deciding how VLAN trunks/native VLANs map onto the bridge node data model;
* teaching Linux bridge nodes to configure VLAN filtering and per-port VLAN membership in a portable way;
* rethinking STP and failure semantics for per-VLAN behavior.

In other words, **transparent trunk transport** is a realistic near-term goal, but **VLAN-aware bridge nodes** are a separate future design effort.

## Bottom Line

Using Linux containers as bridge nodes in pure **clab** topologies is reasonable for:

* simple multi-access segments;
* validation scenarios where you want a controllable in-lab bridge;
* transparent transport of Ethernet frames across a small bridged segment.

It is a poor fit for:

* complex layer-2 fabrics;
* large numbers of bridge-based LAN segments;
* scenarios where the multi-access network itself must be modeled as a VLAN-aware switch;
* realistic testing of native/access/trunk semantics in the middle of the segment.

If we document or recommend this pattern, one point should be very clear: a Linux bridge node is fine for "make a LAN inside a clab-only topology", but it is not a substitute for proper VLAN-aware switching.
