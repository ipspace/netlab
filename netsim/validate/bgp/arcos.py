"""
ArcOS BGP validation over docker-exec + confd_cli.

ArcOS is a native containerlab container (arrcus_arcos); on this build SSH/NETCONF/gNMI are disabled,
so validation reaches the CLI over the SAME docker-exec + confd_cli path config deployment uses
(ansible_connection: docker). netlab_show_command (devices/arcos.yml -> clab.group_vars) wraps the
returned path as:  printf 'show <path> | display json' | confd_cli -C -u admin  -- so _result is the
parsed OpenConfig BGP subtree JSON.  ArcOS speaks OpenConfig JSON, not FRR, so this cannot alias frr
the way sonic_clab does; the checks below walk the OpenConfig tree directly.

Both checks read the whole per-instance BGP subtree (network-instance <vrf> protocol BGP <instance>),
which carries neighbor session-state AND the loc-rib / adj-rib routes, so one show path serves both.
"""
import typing

from netsim.data import global_vars

BGP_INSTANCE: typing.Final[str] = 'b1'   # netlab renders a single default-VRF BGP instance named b1


def _collect(obj: typing.Any, pred: typing.Callable[[dict], bool], out: list) -> None:
  # Recursively collect every dict in the OpenConfig JSON tree for which pred() is true.
  if isinstance(obj, dict):
    if pred(obj):
      out.append(obj)
    for v in obj.values():
      _collect(v, pred, out)
  elif isinstance(obj, list):
    for v in obj:
      _collect(v, pred, out)


def show_bgp_neighbor(peer_as: typing.Any, vrf: str = 'default', instance: str = BGP_INSTANCE,
                      **kwargs: typing.Any) -> str:
  # netlab_show_command wraps this: printf 'show <this> | display json' | confd_cli -C -u admin
  return f'network-instance {vrf} protocol BGP {instance}'


def valid_bgp_neighbor(peer_as: typing.Any, present: bool = True, state: str = 'ESTABLISHED',
                       vrf: str = 'default', instance: str = BGP_INSTANCE,
                       **kwargs: typing.Any) -> str:
  _result = global_vars.get_result_dict('_result')
  # A neighbor's operational state dict carries both 'session-state' and 'peer-as'.
  states: list = []
  _collect(_result, lambda d: 'session-state' in d and 'peer-as' in d, states)
  match = [s for s in states if str(s.get('peer-as')) == str(peer_as)]
  ok = [s for s in match if state in str(s.get('session-state', ''))]
  if ok:
    if not present:
      raise Exception(f'Unexpected {state} BGP neighbor (peer AS {peer_as})')
    return f'ArcOS eBGP neighbor (peer AS {peer_as}) session is {state}'
  if not present:
    return f'BGP neighbor (peer AS {peer_as}) is (correctly) not {state}'
  seen = sorted({f"AS{s.get('peer-as')}={s.get('session-state')}" for s in states})
  raise Exception(f'No {state} BGP neighbor with peer AS {peer_as} on ArcOS; sessions seen: {seen}')


def show_bgp_prefix(pfx: str, vrf: str = 'default', instance: str = BGP_INSTANCE,
                    **kwargs: typing.Any) -> str:
  return f'network-instance {vrf} protocol BGP {instance}'


def valid_bgp_prefix(pfx: str, present: bool = True, vrf: str = 'default', instance: str = BGP_INSTANCE,
                     **kwargs: typing.Any) -> str:
  _result = global_vars.get_result_dict('_result')
  want = str(pfx)
  want_addr = want.split('/')[0]
  # Every route entry (loc-rib, adj-rib-in-post, ...) carries a 'prefix' leaf; receipt of the peer
  # prefix means it shows up as a route in this BGP instance's RIB.
  routes: list = []
  _collect(_result, lambda d: 'prefix' in d and isinstance(d.get('prefix'), str), routes)
  prefixes = {str(r['prefix']) for r in routes}
  hit = want in prefixes or any(p.split('/')[0] == want_addr for p in prefixes)
  if hit:
    if not present:
      raise Exception(f'BGP prefix {want} unexpectedly present in ArcOS RIB')
    return f'ArcOS has BGP prefix {want} in the RIB (received over eBGP)'
  if not present:
    return f'BGP prefix {want} is (correctly) absent'
  raise Exception(f'BGP prefix {want} not in ArcOS RIB; prefixes seen: {sorted(prefixes)}')
