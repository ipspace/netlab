(plugin-tunnel-gre)=
# GRE Tunnels

The **tunnel.gre** plugin implements point-to-point GRE tunnels over IPv4 and IPv6, including the transport (front-door) VRF functionality.

## Supported Platforms

The plugin includes Jinja2 templates for the following platforms:

| Operating system    | GRE over<br>IPv4 | GRE over<br>IPv6 | Transport<br>VRF |
|--------------|:-:|:-:|:-:|
| Cisco IOS/XE[^18v] |✅|✅|✅|
| FRR                 |✅|✅|✅|
| Juniper vJunos-switch |✅|✅|✅|
| Juniper vSRX        |✅|✅|✅|
| Mikrotik RouterOS 7 |✅|✅|✅|
| VyOS               |✅|✅|✅|

[^18v]: Includes Cisco IOSv, Cisco IOSvL2, Cisco CSR 1000v, Cisco Catalyst 8000v, Cisco IOS-on-Linux (IOL), and IOL Layer-2 image.

## Specifying Tunnel Parameters

The GRE tunnels are configured as [links](topo-links) with **tunnel.mode** attribute set to **gre**[^ATT].

[^ATT]: **tunnel.mode** attribute on a link automatically sets link **type** to **tunnel**.

The other link/interface parameters supported by this plugin include:

* **tunnel.af** (`ipv4` or `ipv6`) -- the transport address family (default: `ipv4`)
* **tunnel.vrf** (VRF name) -- the transport VRF (default: global routing table)
* **tunnel.source** -- the [source interface](plugin-tunnel-source) for the tunnel.

(plugin-tunnel-source)=
## Specifying Tunnel Source and Destination

The source interface/IP address for a tunnel is specified with the **tunnel.source** link/interface attribute. This attribute can have these components:

* **ifindex** -- matches the source interface based on its **ifindex** (useful only when you [specify **ifindex** on interfaces](link-attributes-intf))
* **name** -- matches link/interface **name** attribute
* **role** -- matches link/interface **role** attribute
* **type** -- specifies source interface type (valid value: **loopback**)

The source interface selection algorithm evaluates all interfaces in the VRF specified with the **tunnel.vrf** parameter or global interfaces when the tunnel link/interface has no **tunnel.vrf** parameter. The selected interface must match the optional **ifindex**, **name**, or **role** parameters and must have an IP address in the **tunnel.af** address family.

The loopback interface(s) are skipped unless you set the **tunnel.type** attribute to **loopback**. The tunnel interfaces are always skipped[^TIS].

[^TIS]: _netlab_ does not support recursive tunnels. If you have a good use case, open an issue or a discussion.

The tunnel destination does not have to be specified; it's taken from the source interface information of the peer device attached to the same tunnel.

## Example

The following topology builds a two-router network with a GRE tunnel in the global routing table using the **transport** VRF as the tunnel underlay:

```
module: [ ospf, vrf ]

vrfs:
  transport:

nodes:
  r1:
  r2:

links:
- r1:
  r2:
  ospf: False
  vrf: transport
- r1:
  r2:
  tunnel.mode: gre
  tunnel.vrf: transport
```
