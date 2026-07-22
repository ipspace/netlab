# SONiC (containerlab) integration smoke tests

Device-specific bring-up smoke tests for the `sonic_clab` device (docker-sonic-vs on
containerlab). Every topology below has been run live against a real `docker-sonic-vs:latest`
node (containerlab 0.77.0) with `netlab up`/`netlab initial`, all over Ansible's
`docker` connection plugin -- no SSH.

| topology | module(s) exercised | what was checked live |
|---|---|---|
| `01-initial.yml` | initial | 1-node bring-up: hostname, loopback IP, interfaces |
| `02-ospf.yml` | ospf | adjacency Full (pure `ansible_network_os: frr` fallback, no `sonic_clab` template) |
| `03-bgp.yml` | bgp | eBGP session Established (frr fallback) |
| `04-isis.yml` | isis | adjacency Up (frr fallback) |
| `05-vrf.yml` | vrf, ospf | per-VRF OSPF adjacency Full (frr fallback) |
| `06-mpls-sr-l3vpn.yml` | isis, bgp, mpls, sr, vrf | LDP Operational, real kernel MPLS label FIB, VPNv4 Established, L3VPN ping 0% loss. **Needs a one-time host prereq: `sudo modprobe mpls_router mpls_iptunnel`** |
| `07-srv6.yml` | isis, srv6 | real kernel `seg6local` End/End.X routes, cross-node ISIS locator advertisement |
| `08-vlan.yml` | vlan | IRB SVI + kernel bridge datapath, 0% loss (needed a `sonic_clab.j2` override + kernel-sync -- see below) |
| `09-lag.yml` | lag, ospf | LACP aggregate (teamd), OSPF Full over the PortChannel (needed a `sonic_clab.j2` override) |
| `11-vxlan-evpn.yml` | vlan, ospf, bgp, vxlan, evpn | L2VNI up, remote VTEP learned, h1<->h2 ping across the tunnel 0% loss (needed a `sonic_clab.j2` override) |
| `12-evpn-irb-l3vni.yml` | vlan, vrf, ospf, bgp, vxlan, evpn | symmetric-IRB L3VNI inter-subnet ping 0% loss |
| `13-vrf-leak.yml` | vrf, bgp | VRF red's prefix leaks into VRF blue's RIB via BGP RT import |
| `14-bgp-session.yml` | bgp, bgp.session plugin | MD5 password applied, session Established (frr fallback) |
| `15-bgp-policy.yml` | bgp, bgp.policy plugin, routing | route-map locpref/weight/community all applied (frr fallback) |
| `16-ebgp-multihop.yml` | bgp, ebgp.multihop plugin, ospf, routing | loopback-to-loopback multihop session Established (frr fallback) |
| `17-ospf-areas.yml` | ospf, ospf.areas plugin | stub area adjacency Full (frr fallback) |
| `18-bgp-originate.yml` | bgp | originated prefix received by the eBGP peer (frr fallback) |
| `19-bfd.yml` | ospf, bfd | BFD session Up under OSPF (frr fallback; needed `features.ospf.bfd`/`features.bgp.bfd` device flags) |
| `20-ripv2.yml` | ripv2 | route learned via RIP (frr fallback) |
| `21-evpn-multihoming.yml` | lag, vlan, ospf, bgp, vxlan, evpn, evpn.multihoming plugin | Ethernet Segment on PortChannel1, dual-homed h1<->h2 ping 0% loss (needs the `h1-fixaddr/` custom-config addon, a generic `linux`-device host-addressing workaround, not SONiC-specific) |
| `22-ospfv3.yml` | ospf | OSPFv3 dual-stack: both AFs adjacency Full, ping6 0% loss (frr fallback) |
| `23-isis-v6-bgp-v6.yml` | isis, bgp | IS-IS adjacency Up (multi-topology IPv6), iBGP IPv6 AF Established (frr fallback) |
| `24-routing-v6.yml` | routing | IPv6 static route + IPv6 prefix-list both installed (frr fallback) |
| `25-vrf-v6-leak.yml` | vrf, bgp | VRF red's IPv6 prefix leaks into VRF blue's v6 RIB via BGP RT import (frr fallback) |
| `26-vrf-v6-ospfv3.yml` | vrf, ospf | per-VRF OSPFv3 adjacency Full (frr fallback) |
| `27-tunnel-gre.yml` | ospf, tunnel.gre plugin | kernel `ip_gre` tunnel, ping across the tunnel IPs 0% loss (needed an `initial/sonic_clab.j2` fix -- see below; the `tunnel.gre/frr.j2` plugin template itself needed no override) |
| `28-files-maxprefix.yml` | bgp, files plugin | `files` escape-hatch worked example: raw FRR `maximum-prefix 100` configlet injected and applied (frr fallback + our own `deploy-config/sonic_clab.yml`, same mechanism proven for tunnel.gre/evpn.multihoming) |
| `29-bgp-domain.yml` | bgp, ospf, bgp.domain plugin | isolated iBGP domains: s1 keeps exactly 2 (red) peers, the cross-domain s1<->s4 session is pruned, s3 (red) reaches h2 via RR reflection, s4 (blue) has zero BGP neighbors and no route to h2 (frr fallback + netlab-core plugin logic, no device template involved) |

Run with `netlab up <file>` from this directory (needs `docker-sonic-vs:latest` pulled locally
and a `multilab` id that isn't in use -- these default to id 52).

## What actually needed a `sonic_clab.j2` override vs. what's free

Most modules above render and deploy with **zero new template files** -- they fall through
automatically to the package's `<module>/frr.j2` via the `ansible_network_os: frr` search-path
fallback (see `netsim/devices/sonic_clab.yml`'s `group_vars.ansible_network_os` inherited from
the parent `sonic` device). Only these needed a real `sonic_clab.j2`, each verified live here:

* `initial` -- interface/loopback bring-up via the `config` CLI, CONFIG_DB->kernel sync for
  routed ports, FRR daemon enable, sshd bootstrap. config_db VLAN and PortChannel *creation* is
  factored out into the per-module init hooks below (pulled in at the right ordering point by
  `extra_module_initial()`, the same mechanism VyOS uses).
* `vlan/sonic_clab.initial.j2` -- create config_db VLANs (`Vlan<id>`) before any SVI is addressed.
* `vlan` -- switchport membership via `config vlan member add`, **plus a kernel bridge sync**
  (docker-sonic-vs's `vlanmgrd` races at boot and often never mirrors `VLAN_MEMBER` rows written
  during the first deploy -- found live: config_db had the row, but the kernel port had no
  `master Bridge` and cross-node ping failed 100% until the sync was added).
* `lag/sonic_clab.initial.j2` -- create the config_db PortChannel(s) before the aggregate is
  addressed.
* `lag` -- PortChannel members via `config portchannel member add`, plus a defensive `teamdctl`
  sync (teammgrd is more reliable than vlanmgrd, but this belt-and-suspenders step guards the
  rare miss).
* `vxlan` -- EVPN-VXLAN L2VNI/L3VNI built directly on the kernel/FRR path (bridge + kernel vxlan
  netdev), since docker-sonic-vs's orchagent can't program the VXLAN dataplane from CONFIG_DB.
  The EVPN/BGP control plane itself is standard FRR (`bgp/frr.j2` + zebra `advertise-all-vni`);
  this template is only the kernel data-plane setup the VS orchestration agent won't do.

`bgp`, `evpn`, `evpn.multihoming`, `isis`, `vrf`, `mpls`, `sr`, `srv6`, `bfd`, `gateway`,
`routing`, `ripv2`, `tunnel.gre`,
`bgp.session`/`bgp.policy`/`bgp.originate`/`bgp.domain`/`ebgp.multihop`, `ospf.areas`, and the
IPv4/IPv6 dual-stack variants of all of the above need no override at all -- they render via the
frr fallback too. (`bgp` needs no `no router bgp` reset wrapper: unlike the Azure/libvirt sonic
image, docker-sonic-vs does not pre-seed a BGP AS.)

One bug found and fixed by `27-tunnel-gre.yml`: the `initial/sonic_clab.j2` bash/config_db loop
deliberately skips tunnel interfaces (the `config` CLI only accepts Ethernet/PortChannel/
Vlan/Loopback names), and the shared `tunnel.gre/frr.j2` plugin template only creates the kernel
netdev (`ip tunnel add`), it doesn't address it -- so the tunnel interface was created with NO
IP at all until the vtysh heredoc in `initial/sonic_clab.j2` was extended to address
tunnel-type interfaces itself (the same thing the vanilla `frr` device's own initial template
already does for every interface, unconditionally -- our SONiC template only omits it elsewhere
because config_db handles addressing for every other interface type).

Genuinely unsupported on this image, not just untested (see `netsim/devices/sonic_clab.yml`'s
`support.caveats` for the live-probed reasons): DHCP relay/client, real STP port-blocking,
and the `mlag.vtep` active-active datapath.

This is a device bring-up smoke-test set, not (yet) wired into netlab's shared per-module
`tests/integration/<module>/NN-*.yml` parameterized matrix that runs across all devices -- that
wiring is tracked as a follow-up.
