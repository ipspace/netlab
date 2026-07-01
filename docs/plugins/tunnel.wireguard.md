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

The plugin includes Jinja2 templates for the following platforms:

| Operating system | WireGuard tunnels | Transport VRF |
|------------------|:-:|:-:|
| FRR              |✅|✅|

## Using the Plugin

* Add `plugin: [ tunnel.wireguard ]` to the lab topology.
* Create a [point-to-point link](topo-links) between two nodes and set **tunnel.mode** to **wireguard**.

[^ATT]: **tunnel.mode** attribute on a link automatically sets link **type** to **tunnel**.

## Specifying Tunnel Parameters

WireGuard tunnels are configured as [links](topo-links) with **tunnel.mode** attribute set to **wireguard**.

The link/interface parameters supported by this plugin include:

* **tunnel.private_key** (base64 string) -- this node's WireGuard private key
* **tunnel.public_key** (base64 string) -- this node's WireGuard public key
* **tunnel.listen_port** (integer, 1-65535) -- UDP listen port (default: `51820`)
* **tunnel.allowed_ips** (prefix string) -- allowed IPs for the remote peer (default: `0.0.0.0/0`)
* **tunnel.persistent_keepalive** (integer) -- keepalive interval in seconds (default: `25`)
* **tunnel.mtu** (integer) -- tunnel interface MTU (default: `1420`)
* **tunnel.af** (`ipv4` or `ipv6`) -- the transport address family (default: `ipv4`)
* **tunnel.vrf** (VRF name) -- the transport VRF (default: global routing table)
* **tunnel.source** -- the [source interface](plugin-tunnel-wireguard-source) for the tunnel underlay

(plugin-tunnel-wireguard-keys)=
## WireGuard Keys

The plugin can generate WireGuard key pairs during the topology transformation process:

* If neither **tunnel.private_key** nor **tunnel.public_key** is specified, the plugin generates a new key pair for the tunnel interface.
* If only **tunnel.private_key** is specified, the plugin derives **tunnel.public_key** from it.
* If only **tunnel.public_key** is specified, the transformation fails.

Key generation uses the **wireguard-tools** commands (`wg genkey` and `wg pubkey`) when they are available on the host running **netlab create**. Otherwise, the plugin uses the Python **cryptography** library.

The remote peer's **tunnel.public_key** and UDP endpoint do not have to be specified; they are taken from the peer device attached to the same tunnel.

(plugin-tunnel-wireguard-source)=
## Specifying Tunnel Source and Destination

The source interface/IP address for a tunnel is specified with the **tunnel.source** link/interface attribute. This attribute can have these components:

* **ifindex** -- matches the source interface based on its **ifindex** (useful only when you [specify **ifindex** on interfaces](link-attributes-intf))
* **name** -- matches link/interface **name** attribute
* **role** -- matches link/interface **role** attribute
* **type** -- specifies source interface type (valid value: **loopback**)

The source interface selection algorithm evaluates all interfaces in the VRF specified with the **tunnel.vrf** parameter or global interfaces when the tunnel link/interface has no **tunnel.vrf** parameter. The selected interface must match the optional **ifindex**, **name**, or **role** parameters and must have an IP address in the **tunnel.af** address family.

When the source is not pinned to a specific interface, the plugin prefers the underlay interface connected to the tunnel peer. This helps multi-homed nodes select the correct underlay for each tunnel.

The loopback interface(s) are skipped unless you set **tunnel.source.type** to **loopback**. The tunnel interfaces are always skipped.

The tunnel destination does not have to be specified; it's taken from the source interface information of the peer device attached to the same tunnel.

## Device Configuration

On FRR nodes using the **clab** provider, the plugin installs the **wireguard-tools** package during the **initial** device configuration (before the management VRF is created) and configures tunnels with a shell script.

## Examples

(wireguard-tunnel-example)=
### WireGuard tunnel over a routed underlay

The following topology builds a two-router network with a WireGuard tunnel in the global routing table using a **core** link role as the tunnel underlay:

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

(wireguard-tunnel-vrf-example)=
### WireGuard tunnel in a transport VRF

The following topology builds a two-router network with a WireGuard tunnel in the **transport** VRF:

```
plugin: [ tunnel.wireguard ]
module: [ ospf, vrf ]

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

You can find an integration test based on this topology in `tests/integration/tunnel/04-wireguard-vrf.yml`.
