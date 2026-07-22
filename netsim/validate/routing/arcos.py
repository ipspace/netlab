"""
ArcOS static-routing validation over docker-exec + confd_cli.

Same transport as the OSPF/BGP/IS-IS ArcOS plugins: netlab_show_command (devices/arcos.yml ->
clab.group_vars) runs  printf 'show <path> | display json' | confd_cli -C -u admin  over
ansible_connection: docker, so _result is the parsed OpenConfig STATIC subtree JSON.

Read-back path: this ArcOS virtual image does NOT populate an OpenConfig STATIC *operational-state*
/ RIB tree (`show network-instance default protocol STATIC default` returns an empty state
container, and no afts/rib operational path is exposed on the container image), so the check reads
the committed route back over the running-config JSON -- the SAME confd path used to deploy it, so a
present+complete static-route entry proves netlab rendered it and the device accepted+committed it.
Actual FIB install + forwarding on the container is separately verified (kernel `ip route ... proto
static` + end-to-end ping); see docs/caveats.md.
"""
import typing

from netsim.data import global_vars


def _collect(obj: typing.Any, pred: typing.Callable[[dict], bool], out: list) -> None:
  if isinstance(obj, dict):
    if pred(obj):
      out.append(obj)
    for v in obj.values():
      _collect(v, pred, out)
  elif isinstance(obj, list):
    for v in obj:
      _collect(v, pred, out)


def show_route_static(pfx: str, vrf: str = 'default', instance: str = 'default',
                      **kwargs: typing.Any) -> str:
  # netlab_show_command wraps this: printf 'show <this> | display json' | confd_cli -C -u admin
  return f'running-config network-instance {vrf} protocol STATIC {instance}'


def valid_route_static(pfx: str, present: bool = True, nexthop: str = '', vrf: str = 'default',
                       instance: str = 'default', **kwargs: typing.Any) -> str:
  _result = global_vars.get_result_dict('_result')
  want = str(pfx)
  want_addr = want.split('/')[0]
  # Each static-route entry carries a 'prefix' leaf; match on the destination prefix.
  routes: list = []
  _collect(_result, lambda d: 'prefix' in d and isinstance(d.get('prefix'), str)
           and d['prefix'].split('/')[0] == want_addr, routes)
  if not routes:
    if not present:
      return f'Static route {want} is (correctly) absent'
    seen: list = []
    _collect(_result, lambda d: 'prefix' in d and isinstance(d.get('prefix'), str), seen)
    raise Exception(f'No static route for {want} on ArcOS; static prefixes seen: '
                    f'{sorted({str(r["prefix"]) for r in seen})}')
  if not present:
    raise Exception(f'Static route {want} unexpectedly present')
  # A complete static route must carry at least one next-hop; collect next-hop values in the entry.
  nhs: list = []
  _collect(routes[0], lambda d: 'next-hop' in d and isinstance(d.get('next-hop'), str), nhs)
  nh_vals = {d['next-hop'] for d in nhs}
  if not nh_vals:
    raise Exception(f'Static route {want} has no next-hop configured on ArcOS')
  if nexthop and nexthop.split('/')[0] not in {n.split('/')[0] for n in nh_vals}:
    raise Exception(f'Static route {want} next-hop {sorted(nh_vals)} != expected {nexthop}')
  return f'ArcOS has committed static route {want} via next-hop {sorted(nh_vals)}'
