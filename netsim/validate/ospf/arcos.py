"""
ArcOS OSPFv2 validation over docker-exec + confd_cli.

ArcOS is a native containerlab container (arrcus_arcos); on this build SSH/NETCONF/gNMI are disabled,
so validation reaches the CLI over the SAME docker-exec + confd_cli path config deployment uses
(ansible_connection: docker). netlab_show_command (devices/arcos.yml -> clab.group_vars) wraps the
returned path as:  printf 'show <path> | display json' | confd_cli -C -u admin  -- so _result is the
parsed OpenConfig network-instance JSON. Mirrors how sonic_clab validates over docker-exec.
"""
import typing

from netsim.data import global_vars


def _find_neighbors(obj: typing.Any) -> list:
  # Recursively collect OSPF neighbor entries (dicts carrying 'neighbor-router-id') from the
  # confd OpenConfig JSON tree -- robust to the areas/interfaces nesting.
  out: list = []
  if isinstance(obj, dict):
    if 'neighbor-router-id' in obj:
      out.append(obj)
    for v in obj.values():
      out += _find_neighbors(v)
  elif isinstance(obj, list):
    for v in obj:
      out += _find_neighbors(v)
  return out


def show_ospf_neighbor(id: str, present: bool = True, vrf: str = 'default', bfd: bool = False) -> str:
  # netlab_show_command wraps this: printf 'show <this> | display json' | confd_cli -C -u admin
  return f'network-instance {vrf}'


def valid_ospf_neighbor(id: str, present: bool = True, vrf: str = 'default', bfd: bool = False) -> str:
  _result = global_vars.get_result_dict('_result')
  nbrs = _find_neighbors(_result)
  full = [n for n in nbrs
          if str(n.get('neighbor-router-id')) == str(id)
          and 'NEIGHBOR_FULL' in str(n.get('adjacency-state', ''))]
  if full:
    if not present:
      raise Exception(f'Unexpected FULL OSPFv2 neighbor {id}')
    return f'ArcOS OSPFv2 neighbor {id} is FULL'
  if not present:
    return f'OSPFv2 neighbor {id} is (correctly) not adjacent'
  seen = sorted({str(n.get('neighbor-router-id')) for n in nbrs})
  raise Exception(f'No FULL OSPFv2 neighbor {id} on ArcOS; adjacent router-ids seen: {seen}')
