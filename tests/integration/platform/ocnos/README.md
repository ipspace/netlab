# OcNOS integration test

`ospf-bgp.yml` -- minimal two-node OcNOS smoke test (OSPFv2 + iBGP over one
point-to-point link). Exercises the `ocnos` device definition
(`netsim/devices/ocnos.yml`), the `initial`/`ospf`/`bgp` templates, and the
`ipinfusion.ocnos` + `ansible.netcommon.network_cli` config-push path
(`netsim/ansible/tasks/deploy-config/ocnos.yml`).

Requires the `ipinfusion.ocnos` Ansible collection and a real OcNOS clab image
(commercial NOS -- users provide their own, see `netsim/devices/ocnos.yml` clab
image reference):

```
ansible-galaxy collection install ipinfusion.ocnos
export ANSIBLE_COLLECTIONS_PATH=~/.ansible/collections:$(python -c "import netsim,os;print(os.path.dirname(netsim.__file__))")/../ansible_collections

netlab up tests/integration/platform/ocnos/ospf-bgp.yml
```

Verify: OSPF adjacency Full and BGP session Established, e.g.

```
ansible -i hosts.yml r1 -m ipinfusion.ocnos.ocnos_command -a 'commands="show ip ospf neighbor"'
ansible -i hosts.yml r1 -m ipinfusion.ocnos.ocnos_command -a 'commands="show ip bgp summary"'
```

This topology intentionally has no `validate:` block -- see the comment in
`ospf-bgp.yml` for why (OcNOS's cmlsh restricted shell has no non-interactive
exec mode, so netlab's native device-side `show`-command validation path does
not apply; the existing generic module suites in `tests/integration/ospf/` and
`tests/integration/bgp/` validate a device-under-test via probe-node plugin
checks instead, and run unmodified against `-d ocnos`).
