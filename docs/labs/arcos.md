(build-arcos)=
# Installing Arrcus ArcOS

netlab runs **Arrcus ArcOS** as a [containerlab](clab.md)-provisioned device. ArcOS is a
**native** containerlab kind (`arrcus_arcos`) -- no vrnetlab packaging -- and only the **clab**
provider is supported (no Vagrant box).

## Container image

ArcOS is a commercial NOS; there is no public image. Obtain an ArcOS container image and tag it as
the device expects (or point `clab.image` at your own tag):

```
defaults.devices.arcos.clab.image: arcos:8.2.1A.P2
```

The device sets clab `kind: arrcus_arcos`. Verified against the **8.2.1A.P2** container image.

## First-boot bootstrap

The tested image boots with SSH, NETCONF, and gNMI disabled, and ArcOS refuses to enable
interfaces until the factory-default admin-user password is changed. netlab handles both
automatically with the native `netlab_start_exec` group variable (containerlab's post-start
`exec:`): it enables `ssh-server`, sets the admin-user password, and creates an AAA user before any
configuration is deployed. No manual steps are required.

## Configuration deployment

ArcOS uses netlab's native containerlab **"sh" config mode**
([Linux configuration scripts](../dev/config/deploy.md)): each configuration module is rendered into
`/config/netlab/NN-<module>.sh` with a `#!/config/netlab/netlab-config.sh` shebang and deployed with
`docker exec`, which hands the rendered config to the mapped wrapper
`netsim/templates/provider/clab/arcos/netlab-config.j2` to load through `confd_cli`
(`load merge` / `commit`). No Ansible is used to deploy configuration -- this is the same
mapped-script pattern Juniper cRPD uses. `ansible_connection: docker` is retained only for the
validation/collect path.

ArcOS also ships the official `arrcus.arcos` `network_cli` collection (the project-recommended
interactive model), but every published version hangs against this image; see the
[ArcOS caveats](caveats-arcos). No extra Ansible collection is required.

## Supported configuration modules

`initial`, `ospf` (v2/v3), `bgp`, `isis`, `vrf` (+ospf/isis/bgp), `vlan`, `lag`, `gateway` (VRRP),
`dhcp`/relay, `bfd`, `routing` (static/prefix-set/policy), `mpls` (LDP), `sr` (SR-MPLS via IS-IS),
`srv6`, `vxlan`, and `evpn` (L2VNI). See `netsim/devices/arcos.yml` `features:` for the
authoritative list; support level is **best-effort** (see [caveats](caveats-arcos)).

VLANs use the native switched-VLAN model (`vlan <id>` plus `interface ... ethernet switched-vlan`),
and SVIs are named `vlan<id>`. Routing-protocol instances inside a VRF are tagged with the VRF name,
because a protocol instance tag is a single global namespace across every network instance on this
build.

## Validation

`netlab validate` reads ArcOS device state over the same docker-exec path used to deploy config
(`show <path> | display json | confd_cli`, parsed as OpenConfig JSON by
`netsim/validate/**/arcos.py`) -- netlab's standard device-side show-command validation, with no
SSH/NETCONF/gNMI and no `ansible` validation action. ArcOS is exercised with netlab's regular
[integration tests](../dev/integration-tests.md).
