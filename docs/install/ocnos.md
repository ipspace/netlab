# Installing IP Infusion OcNOS

netlab runs **IP Infusion OcNOS** as a [containerlab](clab.md)-provisioned device: a vrnetlab-packaged
OcNOS VM. Only the **clab** provider is supported (no Vagrant box).

## Container image

* Build the vrnetlab OcNOS container from the OcNOS `qcow2` using vrnetlab's `ipinfusion_ocnos` kind.
* Tag it `vrnetlab/ipinfusion_ocnos:<version>`. Verified against **7.0.0-262** (and 6.5.2-101).
* The device sets clab `kind: ipinfusion_ocnos`; point it at your image:

```
defaults.devices.ocnos.clab.image: vrnetlab/ipinfusion_ocnos:7.0.0-262
```

## Configuration deployment

OcNOS configuration is pushed with the **`ipinfusion.ocnos` Ansible collection** over `network_cli`
(the collection drives the interactive `cmlsh` shell). Install it once:

```
ansible-galaxy collection install ipinfusion.ocnos
```

The same collection is used to read device state during `netlab validate` (see the validation
note below). Device settings: `interface_name eth{ifindex}`, `mgmt_if eth0`, loopbacks
`lo`/`loopbackN`.

## Supported configuration modules

`initial`, `ospf` (+areas/NSSA), `bgp` (+plugins/policy/multihop), `isis`, `vrf` (+isis), `vlan`,
`lag` (+passive), `gateway`, `dhcp`/relay, `stp`, `mpls`, `sr` (SRGB), `vxlan`, `evpn` (MPLS), `bfd`,
`gre`. See `netsim/devices/ocnos.yml` `features:` for the authoritative list; support level is
**best-effort** (see `docs/caveats.md`).

## Validation with the `ansible` action (`netlab validate`)

OcNOS's `ocnos` user has a **restricted shell**: it drops into `cmlsh` only on an *interactive*
login. `ssh ocnos@node "show ..."` (and every `cmlsh -e/-c` variant) returns ``Try `cmlsh --help'`` --
there is **no non-interactive exec** -- and OcNOS emits CLI **text**, not JSON. netlab's SSH and
`docker exec` validation transports therefore cannot drive OcNOS show commands.

OcNOS uses the **`ansible` validation action** instead -- a validation data *source* (a peer of
`netsim/cli/validate/suzieq.py`, implemented in `netsim/cli/validate/ansible.py`), **not** a
connection-method change (`netsim/cli/connect.py` is unchanged). A validation test selects it with
an `ansible` action or a validation-plugin `ansible_<test>()` function that supplies the show
command; the device names the Ansible module to run it through in `netsim/devices/ocnos.yml`:

```
netlab_validate:
  ansible_module: ipinfusion.ocnos.ocnos_command
```

`netlab validate` then runs the show command through `ipinfusion.ocnos.ocnos_command` against the
netlab-generated inventory. The result is parsed as JSON when the command emits it, otherwise the
CLI text is returned in `stdout`; the OcNOS validators (`netsim/validate/<module>/ocnos.py`,
re-exported from `netsim/validate/ocnos.py`) screen-scrape that text. The action is generic -- any
device whose CLI lacks a non-interactive SSH exec can opt in the same way.

Run the standard integration suite against an OcNOS device under test:

```
export NETLAB_DEVICE=ocnos NETLAB_PROVIDER=clab
netlab up  tests/integration/ospf/ospfv2/01-network.yml
netlab validate
```

Verified live (vrnetlab `ipinfusion_ocnos:7.0.0-262`, FRR probes): the OSPF, BGP and IS-IS
integration tests pass with native `netlab validate`, and DUT-side neighbor/prefix checks pass
over the Ansible transport.

## Validated modules (native `netlab validate`)

Live-verified against vrnetlab `ipinfusion_ocnos:7.0.0-262` with FRR / cEOS / Linux probes,
using the `ansible` validation action described above. "Probe" = the check runs on the
adjacent probe (interop); "DUT" = the check runs on the OcNOS device via the `ansible` action.

| Module | Integration test | Result |
|---|---|---|
| ospf (v2) | `ospf/ospfv2/01-network` | PASS 4/4 (probe) + 3/3 (DUT: neighbor Full, route present) |
| bgp | `bgp/01-ebgp-session` | PASS 3/3 (probe) + 3/3 (DUT: sessions Established, prefix present) |
| isis | `isis/01-ipv4` | PASS 5/5 (probe) + 2/2 (DUT: adjacency L1, prefix present) — needed the `dynamic-hostname` fix |
| vlan | `vlan/01-vlan-bridge-single` | PASS 1/1 (host-to-host ping across the bridge) |
| lag | `lag/01-l3-lag` | PASS (LAG active on both EOS probes + IPv4 ping; one warning-level path-MTU check) |
| stp | `stp/01-stp-priority` | PASS 2/2 (link forwarding + root-bridge priority) — needed the bridge-priority fix |
| gateway | `gateway/02-vrrp` | IPv4 VRRP fully green (VIP ping, backup/master/preempt). IPv6 VRRP control-plane green (master election + backup/master/preempt) + steady-state datapath — needed the IPv6-VRRP fix. See exception for the v6-transit-on-failover gap. |
| vrf | `vrf/11-multi-vrf-ospf` | Single-area VRF fully green (per-VRF adjacency, routes, ping, inter-VRF isolation). See exception below for the multi-area sub-case. |

Three config-completeness fixes came out of this pass: IS-IS `dynamic-hostname` (peers can map the
DUT system-id to a name), the STP customer-bridge `priority` (was never rendered), and IPv6 VRRP
(the gateway template rendered IPv4 VRRP only; VRRPv3 needs a link-local primary virtual-ipv6).

## Documented exceptions

A "full" device may ship with clearly-documented exceptions; these are recorded rather than faked.

* **Multi-area OSPF inside a VRF** (`vrf/11` blue sub-case). OcNOS is a strict (Cisco-type) ABR: it
  will not originate inter-area type-3 summaries when its backbone (area 0) is *inactive* — here the
  VRF's only area-0 interface is a stub loopback, so two non-backbone areas connected only through the
  DUT do not exchange routes. (OSPF-in-VRF also defaults to MPLS-VPN "superbackbone" mode;
  `capability vrf-lite` clears that but not the inactive-backbone rule.) FRR/EOS are lenient ABRs and
  summarize anyway. Single-area VRF OSPF is unaffected and passes.
* **gateway / VRRP — IPv6 transit forwarding on failover.** The module boots and validates on stock
  clab (an earlier boot failure was a bug in a local `clab-render-mtu` change, not netlab core — MTU
  is handled device-side). IPv4 VRRP is fully green; IPv6 VRRP is now configured (VRRPv3, link-local
  primary virtual address) and control-plane-verified — the DUT wins/holds master and the probe sees
  correct backup/master/preempt transitions, and the v6 datapath pings in steady state. The remaining
  gap: after the VRRP peer's LAN link drops, IPv6 *transit* forwarding through the DUT fails even
  though it is master and the client's neighbor cache holds the virtual MAC — an OcNOS v6-VRRP
  failover-forwarding edge (IPv4 failover is unaffected).
* **dhcp relay** — the 3-piece OcNOS relay config generates and parser-checks correctly, but the
  `dhcp/11-ipv4-relay` integration test needs a libvirt-based `dnsmasq` server probe, unavailable
  on a clab-only host, so the end-to-end relay datapath is not covered by the integration suite.
* **EVPN datapath**, **GRE tunnel line-protocol**, **VRF-bound-interface ingress**, and
  **per-VRF OSPFv3 + IPv6 VRF route-leak** — tracked platform/image limitations; config
  generation is present where applicable.
