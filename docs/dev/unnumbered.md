# Unnumbered Interfaces

*netlab* supports unnumbered IPv4, IPv6 (LLA) or dual-stack interfaces. There are two ways to create an unnumbered interface (or link):

* Set **unnumbered: true** on interface[^NLA] or link.
* Set **ipv4** and/or **ipv6** attribute to *True*.

**unnumbered** attribute is translated into **ipv4** and/or **ipv6** attributes set to *True* based on address families configured on node's loopback interface. With the default addressing setup, **unnumbered: True** results in **ipv4: True**, to enable dual-stack unnumbered interfaces with **unnumbered** attribute, add **ipv6** prefix to the **loopback** addressing pool. For more details, see [unnumbered interfaces](addressing-unnumbered) part of [addressing](../addressing.md) document.

## Implementing unnumbered interfaces

There is no standard way of implementing IPv4 unnumbered interfaces, and they might not be available on all platforms. IPv4 implementations of unnumbered interfaces usually use the loopback IPv4 address as the interface IPv4 address. For more details, read the [unnumbered interfaces](https://blog.ipspace.net/series/unnumbered-interfaces.html) series of blog posts on ipSpace.net.

Unnumbered IPv6 interfaces should use link-local addresses, a standard IPv6 feature.

If your device supports IPv6 LLA-only interface, set `topology-defaults.yml` attribute **devices._name_.features.initial.ipv6.lla** to *True*.

If your device supports IPv4 unnumbered interfaces, set `topology-defaults.yml` attribute **devices._name_.features.initial.ipv4.unnumbered** to *True*.

## Integration with IGP routing protocols

OSPF and IS-IS implementations might support unnumbered IPv4 interfaces[^OSPFv3]. The routing protocol configuration modules detect unnumbered IPv4 interfaces by checking the **unnumbered** and **ipv4** attributes -- if either one of them is set to *True*, the interface is an unnumbered IPv4 interface.

OSPFv2 can use unnumbered IPv4 interfaces on point-to-point links. If your device supports this functionality, set `topology-defaults.yml` attribute **devices._name_.features.ospf.unnumbered** to *True*. OSPFv2 cannot run over multi-access unnumbered IPv4 links.

Some IS-IS implementations support unnumbered IPv4 P2P links. If your device supports this, set `topology-defaults.yml` attribute **devices._name_.features.isis.unnumbered.ipv4** to *True*.

Fewer IS-IS implementations support unnumbered multi-access IPv4 links. To indicate your device can do that, set `topology-defaults.yml` attribute **devices._name_.features.isis.unnumbered.network** to *True*.

```{note}
If you're unsure what your device can do, set all three feature flags to *True*, start a lab, and check whether the adjacency- and routing tables are populated as expected.
```

## Unnumbered EBGP sessions

Several vendors implemented EBGP sessions between well-known IPv6 LLA addresses[^EBGP_LLA]. *netlab* does not support this half-baked attempt and implements IPv6 LLA sessions only for those devices that can configure EBGP session *on an interface*.

Devices supporting interface-level EBGP sessions between auto-generated IPv6 LLA can use these sessions to:

* Transport IPv6 prefixes with LLA next hop over IPv6 AF
* Transport IPv4 prefixes with IPv6 LLA next hop according to RFC 8950.

*netlab* core and BGP configuration module do not support:

* Running IPv4 AF with IPv4 next hops over IPv6 transport session
* Running IPv4 AF with RFC 8950-style IPv6 next hops over numbered IPv6 interfaces or over IBGP sessions.
* Creating IBGP sessions between IPv6 LLA addresses

```{note}
You can always extend *netlab* functionality with plugins and custom configuration modules.
```

*netlab* will create an IPv6 LLA EBGP session whenever it finds a pair of devices connected to the same link if the devices:

* Belong to different autonomous systems
* Have **ipv6** interface attribute set to *True*.

Whenever *netlab* encounters an EBGP session between IPv6 LLA interfaces, it sets **local_if** attribute in the neighbor data structure to simplify the device configuration templates.

If your device supports EBGP sessions between auto-generated IPv6 link-local addresses, set `topology-defaults.yml` attribute **devices._name_.features.bgp.ipv6_lla** to *True*.

*netlab* device configuration templates will enable RFC 8950-style IPv4-over-IPv6 address family on IPv6 LLA sessions if the interface has **ipv6** interface attribute set to *True* (indicating IPv6 LLA EBGP session) AND **ipv4** interface attribute set to *True*.

RFC 8950-style IPv4 address family [REALLY SHOULD NOT](https://www.rfc-editor.org/rfc/rfc6919#section-3) be enabled for:

* EBGP sessions running on numbered IPv6 interfaces
* Interfaces with IPv4 addresses regardless of the state of **ipv6** attribute.

BGP configuration module simplifies the device configuration templates conforming to the above restriction with the **ipv4_rfc8950** neighbor attribute which is set:

* when link or interface **unnumbered** attribute is set to *True* on both EBGP neighbors or
* when both IPv4 and IPv6 interface attributes are set to *True* on both EBGP neighbors.

If your device supports RFC 8950 (IPv4 with IPv6 next hops) on EBGP sessions between auto-generated IPv6 link-local addresses, set `topology-defaults.yml` attribute **devices._name_.features.bgp.rfc8950** to *True*.

[^NLA]: node-to-link attachment

[^OSPFv3]: OSPFv3 runs over IPv6 LLA. Decent IS-IS implementations should support IPv6 LLA-only segments. *netlab* therefore does not check whether an implementation supports IPv6 LLA-only segments.

[^EBGP_LLA]: An EBGP neighbor has to be configured using remote IPv6 LLA address and an interface name.
