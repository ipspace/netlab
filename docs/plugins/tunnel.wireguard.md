(plugin-tunnel-wireguard)=
# WireGuard Tunnels

The **tunnel.wireguard** plugin implements point-to-point WireGuard tunnels over IPv4 and IPv6, including the transport (front-door) VRF functionality.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

## Supported Platforms

You can use WireGuard tunnels with these platforms:

```{features}
- title: WireGuard<br>Tunnels
  enabled: tunnel.wireguard
- title: Transport<br>VRF
  enabled: |-
    'vrf' in tunnel.wireguard
```

```{tip}
See the [integration test results](https://release.netlab.tools/_html/coverage.tunnel) for more details.
```

## Using the Plugin

* Add `plugin: [ tunnel.wireguard ]` to the lab topology.
* Create a [point-to-point link](topo-links) between two nodes and set **tunnel.mode** to **wireguard**.

## Specifying Tunnel Parameters

WireGuard tunnels are configured as [links](topo-links) with **tunnel.mode** attribute set to **wireguard**.

The link/interface parameters supported by this plugin include:

* **tunnel.private_key** (base64 string) -- this node's WireGuard private key (auto-generated when missing)
* **tunnel.public_key** (base64 string) -- this node's WireGuard public key (derived or auto-generated when missing)
* **tunnel.listen_port** (integer, 1-65535) -- UDP listen port. When omitted, the plugin allocates a unique port per tunnel on each node, starting at `51820`[^CPD]
* **tunnel.allowed_ips** (prefix string) -- the peer's WireGuard [allowed IPs](plugin-tunnel-wireguard-allowed-ips) (default: a default route per active address family, so `0.0.0.0/0`, `::/0`, or both `0.0.0.0/0,::/0` for a dual-stack tunnel)
* **tunnel.persistent_keepalive** (integer) -- keepalive interval in seconds (default: `25`)
* **mtu** (integer) -- the WireGuard tunnel interface MTU (the standard link/interface `mtu` attribute). When not specified, it is derived from the underlay source interface MTU minus the WireGuard encapsulation overhead (60 bytes for an IPv4 underlay, 80 bytes for an IPv6 underlay), so it scales with jumbo-frame underlays. With a 1500-byte underlay this yields `1440` for IPv4 transport and `1420` for IPv6 transport.
* **tunnel.af** (`ipv4` or `ipv6`) -- the transport address family. When not specified, it is inferred from the underlay source interface: `ipv4` when an IPv4 address is available, `ipv6` for an IPv6-only underlay.
* **tunnel.vrf** (VRF name) -- the transport VRF (default: global routing table)
* **tunnel.source** -- the [source interface](plugin-tunnel-wireguard-source) for the tunnel underlay

[^CPD]: The starting UDP port can be changed in plugin defaults.

(plugin-tunnel-wireguard-keys)=
## WireGuard Keys

You do not have to specify WireGuard keys in the lab topology. During the topology transformation process, the plugin can generate or derive them automatically:

* If neither **tunnel.private_key** nor **tunnel.public_key** is specified, the plugin generates a new key pair for the tunnel interface.
* If only **tunnel.private_key** is specified, the plugin derives **tunnel.public_key** from it.
* If only **tunnel.public_key** is specified, the transformation fails.

Key generation uses the **wireguard-tools** commands (`wg genkey` and `wg pubkey`), which must be available on the host running **netlab create**. If **wireguard-tools** is not installed, the transformation fails; in that case, either install the package or specify both **tunnel.private_key** and **tunnel.public_key** in the lab topology.

The remote peer's **tunnel.public_key** and UDP endpoint do not have to be specified; they are taken from the peer device attached to the same tunnel.

Specify **tunnel.private_key**, **tunnel.public_key**, and **tunnel.listen_port** only when you need stable keys across lab recreations or a specific UDP port. When **tunnel.listen_port** is omitted, each tunnel on a node gets a unique port starting at `51820`[^CPD].

(plugin-tunnel-wireguard-allowed-ips)=
## Allowed IPs

**tunnel.allowed_ips** maps to WireGuard's *allowed IPs* (its cryptokey-routing table) for the remote peer. It is not an ACL applied to the transport (underlay) traffic; it filters the **inner** packets carried by the tunnel and serves two purposes at once:

* **Outbound** -- only inner packets whose destination falls within **tunnel.allowed_ips** are encrypted and sent to the peer. Packets to any other destination are not routed into the tunnel.
* **Inbound** -- decrypted packets are accepted only if their source address falls within **tunnel.allowed_ips**; anything else is dropped.

These tunnels are point-to-point with a single peer and typically run a dynamic routing protocol (OSPF or OSPFv3) over the tunnel, where the set of prefixes reachable across the tunnel is not known in advance. The plugin therefore defaults **tunnel.allowed_ips** to a default route per active address family so that any inner traffic and any dynamically learned next hop is permitted in both directions. The active address families are taken from the transport VRF when the tunnel is in a VRF, otherwise from the node's global routing table, so a dual-stack tunnel defaults to `0.0.0.0/0,::/0`.

Set **tunnel.allowed_ips** to a narrower prefix only when you want to restrict which inner destinations may traverse the tunnel (for example, a static point-to-point tunnel without a routing protocol). The value applies to a single peer, so it must be wide enough to cover every inner prefix you expect that peer to send or receive.

(plugin-tunnel-wireguard-source)=
## Specifying Tunnel Source and Destination

The source interface/IP address for a tunnel is specified with the **tunnel.source** link/interface attribute. This attribute can have these components:

* **linkid** -- matches the transport interface [link identifier](link-linkid)
* **type** -- specifies source interface type (valid value: **loopback**)
* **link.name** -- matches link/interface **name** attribute
* **link.role** -- matches link/interface **role** attribute
* **ifindex** -- matches the source interface based on its **ifindex** (useful only when you [specify **ifindex** on interfaces](link-attributes-intf))

The source interface selection algorithm evaluates all interfaces in the VRF specified with the **tunnel.vrf** parameter or global interfaces when the tunnel link/interface has no **tunnel.vrf** parameter. The selected interface must match the specified **tunnel.source** and **tunnel.af** parameters.

When the source is not pinned to a specific interface, the plugin prefers the underlay interface connected to the tunnel peer. This helps multi-homed nodes select the correct underlay for each tunnel.

The loopback interface(s) are skipped unless you set **tunnel.source.type** to **loopback**. The tunnel interfaces are always skipped.

The tunnel destination does not have to be specified; it's taken from the source interface information of the peer device attached to the same tunnel.

## Device Configuration

The plugin works on FRR nodes with either the **clab** or **libvirt** provider. It adds the **wireguard-tools** package to the node's package list, which is installed during the **initial** device configuration (on the **clab** provider, before the management VRF is created). Tunnels are then configured with a shell script deployed after the **vrf** module (when used).

The device configuration script:

* Creates the WireGuard interface, configures the peer, and waits up to 60 seconds for the WireGuard handshake to complete.
* Assigns a link-local IPv6 address to the tunnel interface when **tunnel.af** is **ipv6**. WireGuard interfaces do not get a kernel-assigned link-local address; OSPFv3 needs one to form adjacencies over the tunnel.
* Configures transport-VRF underlay routing when **tunnel.vrf** is set. The WireGuard interface stays in the global routing table; encrypted packets are marked with **fwmark** and steered into the transport VRF routing table with a policy routing rule. It also enables **net.ipv4.udp_l3mdev_accept** so the global WireGuard listening socket accepts packets arriving on the VRF underlay. That sysctl governs both IPv4 and IPv6 UDP sockets (there is no **net.ipv6** counterpart), so it applies to IPv4 and IPv6 transport tunnels alike.

## Examples

(wireguard-tunnel-example)=
### WireGuard tunnel over a routed underlay

The following topology builds a two-router network with a WireGuard tunnel in the global routing table using a **core** link role as the tunnel underlay. WireGuard keys are auto-generated; you only have to specify the tunnel type and underlay source:

```
plugin: [ tunnel.wireguard ]
module: [ ospf ]

links:
- r1:
  r2:
  role: core
- r1:
  r2:
  tunnel.mode: wireguard
  tunnel.source.link.role: core
```

You can find an integration test based on this topology in `tests/integration/tunnel/03-wireguard.yml`.

(wireguard-tunnel-vrf-ipv6-example)=
### WireGuard tunnel in a transport VRF with IPv6 transport

Set **tunnel.vrf** to run the WireGuard underlay in a transport VRF while keeping the tunnel interface and routing protocols such as OSPFv3 in the global routing table. The IPv6 transport address family is inferred from the IPv6-only underlay:

```
plugin: [ tunnel.wireguard ]
module: [ ospf, vrf ]

addressing:
  loopback:
    ipv4: False
    ipv6: 2001:db8:1::/48
  lan:
    ipv4: False
    ipv6: 2001:db8:2::/48
  p2p:
    ipv4: False
    ipv6: 2001:db8:3::/48

vrfs:
  transport:

links:
- r1:
  r2:
  vrf: transport
- r1:
  r2:
  tunnel.mode: wireguard
  tunnel.vrf: transport
```

You can find a dual-stack integration test based on this topology in `tests/integration/tunnel/06-wireguard-vrf-dual-stack.yml`.
