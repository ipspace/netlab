"""
ArcOS IS-IS validation over docker-exec + confd_cli.

Same transport as the OSPF/BGP ArcOS plugins: netlab_show_command (devices/arcos.yml ->
clab.group_vars) runs  printf 'show <path> | display json' | confd_cli -C -u admin  over
ansible_connection: docker, so _result is the parsed OpenConfig IS-IS subtree JSON. ArcOS speaks
OpenConfig JSON (not FRR), so these walk the OC tree directly rather than aliasing frr.
"""
import typing

from netsim.data import global_vars

ISIS_INSTANCE: typing.Final[str] = 'i1'   # netlab renders a single default-VRF IS-IS instance named i1


def _collect(obj: typing.Any, pred: typing.Callable[[dict], bool], out: list) -> None:
  if isinstance(obj, dict):
    if pred(obj):
      out.append(obj)
    for v in obj.values():
      _collect(v, pred, out)
  elif isinstance(obj, list):
    for v in obj:
      _collect(v, pred, out)


def show_isis_neighbor(sysid: str = '', present: bool = True, vrf: str = 'default',
                       instance: str = ISIS_INSTANCE, **kwargs: typing.Any) -> str:
  return f'network-instance {vrf} protocol ISIS {instance}'


def valid_isis_neighbor(sysid: str = '', present: bool = True, state: str = 'UP', vrf: str = 'default',
                        instance: str = ISIS_INSTANCE, **kwargs: typing.Any) -> str:
  _result = global_vars.get_result_dict('_result')
  adj: list = []
  _collect(_result, lambda d: 'adjacency-state' in d, adj)
  if sysid:
    adj = [a for a in adj
           if str(sysid) in (str(a.get('neighbor-sysid', '')) + str(a.get('system-id', '')))]
  up = [a for a in adj if state in str(a.get('adjacency-state', ''))]
  if up:
    if not present:
      raise Exception(f'Unexpected {state} IS-IS adjacency {sysid or ""}')
    who = sysid or up[0].get('neighbor-sysid', up[0].get('system-id', ''))
    return f'ArcOS IS-IS adjacency {who} is {state}'
  if not present:
    return f'IS-IS adjacency {sysid or ""} is (correctly) not {state}'
  seen = sorted({str(a.get('adjacency-state')) for a in adj})
  raise Exception(f'No {state} IS-IS adjacency {sysid or ""} on ArcOS; adjacency states seen: {seen}')


def show_isis_prefix(pfx: str, vrf: str = 'default', instance: str = ISIS_INSTANCE,
                     **kwargs: typing.Any) -> str:
  return f'network-instance {vrf} protocol ISIS {instance}'


def valid_isis_prefix(pfx: str, present: bool = True, vrf: str = 'default', instance: str = ISIS_INSTANCE,
                      **kwargs: typing.Any) -> str:
  _result = global_vars.get_result_dict('_result')
  want = str(pfx)
  want_addr = want.split('/')[0]
  # IS-IS reachability prefixes appear as 'prefix'/'ip-prefix' leaves in the LSDB reachability TLVs.
  hits: list = []
  _collect(_result, lambda d: any(str(d.get(k, '')).split('/')[0] == want_addr
                                  for k in ('prefix', 'ip-prefix')), hits)
  if hits:
    if not present:
      raise Exception(f'IS-IS prefix {want} unexpectedly present')
    return f'ArcOS has IS-IS reachability for {want}'
  if not present:
    return f'IS-IS prefix {want} is (correctly) absent'
  raise Exception(f'IS-IS prefix {want} not found in ArcOS IS-IS reachability')
