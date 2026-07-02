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

* **tunnel.private_key** (base64 string) -- this node's WireGuard private key (auto-generated when missing)
* **tunnel.public_key** (base64 string) -- this node's WireGuard public key (derived or auto-generated when missing)
* **tunnel.listen_port** (integer, 1-65535) -- UDP listen port (default: `51820`)
* **tunnel.allowed_ips** (prefix string) -- allowed IPs for the remote peer (default: `0.0.0.0/0`)
* **tunnel.persistent_keepalive** (integer) -- keepalive interval in seconds (default: `25`)
* **tunnel.mtu** (integer) -- tunnel interface MTU (default: `1420`)
* **tunnel.af** (`ipv4` or `ipv6`) -- the transport address family (default: `ipv4`)
* **tunnel.vrf** (VRF name) -- the transport VRF (default: global routing table)
* **tunnel.source** -- the [source interface](plugin-tunnel-wireguard-source) for the tunnel underlay

(plugin-tunnel-wireguard-keys)=
## WireGuard Keys

You do not have to specify WireGuard keys in the lab topology. During the topology transformation process, the plugin can generate or derive them automatically:

* If neither **tunnel.private_key** nor **tunnel.public_key** is specified, the plugin generates a new key pair for the tunnel interface.
* If only **tunnel.private_key** is specified, the plugin derives **tunnel.public_key** from it.
* If only **tunnel.public_key** is specified, the transformation fails.

Key generation uses the **wireguard-tools** commands (`wg genkey` and `wg pubkey`), which must be available on the host running **netlab create**. If **wireguard-tools** is not installed, the transformation fails; in that case, either install the package or specify both **tunnel.private_key** and **tunnel.public_key** in the lab topology.

The remote peer's **tunnel.public_key** and UDP endpoint do not have to be specified; they are taken from the peer device attached to the same tunnel.

Specify **tunnel.private_key**, **tunnel.public_key**, and **tunnel.listen_port** only when you need stable keys across lab recreations or non-default UDP ports.

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

On FRR nodes using the **clab** provider, the plugin installs the **wireguard-tools** package during the **initial** device configuration (before the management VRF is created) and configures tunnels with a shell script deployed after the **vrf** module (when used).

The device configuration script:

* Creates the WireGuard interface, configures the peer, and waits up to 60 seconds for the WireGuard handshake to complete.
* Assigns a link-local IPv6 address to the tunnel interface when **tunnel.af** is **ipv6**. WireGuard interfaces do not get a kernel-assigned link-local address; OSPFv3 needs one to form adjacencies over the tunnel.
* Configures transport-VRF underlay routing when **tunnel.vrf** is set. The WireGuard interface stays in the global routing table; encrypted packets are marked with **fwmark** and steered into the transport VRF routing table with a policy routing rule. IPv4 transport tunnels also enable **net.ipv4.udp_l3mdev_accept**.

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

(wireguard-tunnel-vrf-example)=
### WireGuard tunnel in a transport VRF

The following topology builds a two-router network with a WireGuard tunnel in the **transport** VRF. Keys are auto-generated here as well:

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

You can find an integration test based on this topology in `tests/integration/tunnel/04-wireguard-vrf.yml`. That test uses explicit keys and a non-default **tunnel.listen_port** to keep UDP ports stable across lab runs.

(wireguard-tunnel-ipv6-example)=
### WireGuard tunnel over IPv6 transport

The following topology builds a WireGuard tunnel with IPv6 transport addresses and OSPFv3 over the tunnel. Set **tunnel.allowed_ips** to **::/0** for IPv6 tunnels:

```
plugin: [ tunnel.wireguard ]
module: [ ospf ]

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

links:
- r1:
  r2:
  role: core
- r1:
  r2:
  tunnel.mode: wireguard
  tunnel.af: ipv6
  tunnel.allowed_ips: ::/0
  tunnel.source.link.role: core
```

You can find an integration test based on this topology in `tests/integration/tunnel/05-wireguard-ipv6.yml`.

(wireguard-tunnel-vrf-ipv6-example)=
### WireGuard tunnel in a transport VRF with IPv6 transport

Combine **tunnel.vrf** and **tunnel.af: ipv6** to run the WireGuard underlay in a transport VRF while keeping the tunnel interface and routing protocols such as OSPFv3 in the global routing table:

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
  tunnel.af: ipv6
  tunnel.allowed_ips: ::/0
  tunnel.vrf: transport
```

You can find an integration test based on this topology in `tests/integration/tunnel/06-wireguard-vrf-ipv6.yml`.
