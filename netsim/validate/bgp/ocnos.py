"""
OcNOS BGP validation via the `ansible` validation action (netsim/cli/validate/ansible.py).

`ansible_<test>()` returns the OcNOS show command, netlab runs it through the
ipinfusion.ocnos Ansible module, and `valid_<test>()` asserts on the CLI text.
Function signatures mirror netsim/validate/bgp/frr.py so the stock BGP integration
tests (plugin: bgp_neighbor(node.bgp.neighbors,'dut'), bgp_prefix('...')) work when
the OcNOS node is the target of the check. OcNOS emits CLI text, so we parse the
`show ip bgp summary` / `show bgp <af> summary` tables rather than JSON.
"""

import re
import typing

from box import Box

from netsim.data import global_vars

from .. import _common

# OcNOS `show ip bgp summary` non-Established states (the State/PfxRcd column shows
# one of these words instead of a numeric prefix count).
_BGP_STATE_WORDS = {'Idle', 'Active', 'Connect', 'OpenSent', 'OpenConfirm', 'Idle(Admin)'}


def _row_established(row: typing.List[str]) -> bool:
  # Row layout: Neighbor V AS MsgRcv MsgSen TblVer InQ OutQ Up/Down State/PfxRcd [Desc]
  # Established -> the State/PfxRcd column is a numeric prefix count. The trailing
  # Desc column (peer description) means the last token is NOT reliably the state,
  # so anchor on the Up/Down time column and read the token right after it.
  if any(t in _BGP_STATE_WORDS for t in row):
    return False
  for i, t in enumerate(row):
    if re.fullmatch(r'\d+:\d+:\d+', t) or re.fullmatch(r'\d+[dwmy]\d*[hms]?', t) or t == 'never':
      return i + 1 < len(row) and row[i + 1].replace('+', '').isdigit()
  return False


def _text(_result: typing.Any) -> str:
  if isinstance(_result, (Box, dict)):
    out = _result.get('stdout', '')
    return '\n'.join(out) if isinstance(out, list) else str(out)
  return str(_result or '')


# af -> OcNOS "show" summary command
_AF_SUMMARY = {
    'ipv4': 'show ip bgp summary',
    'ipv6': 'show bgp ipv6 unicast summary',
}
_AF_TABLE = {
    'ipv4': 'show ip bgp',
    'ipv6': 'show bgp ipv6 unicast',
}


def ansible_bgp_neighbor(ngb: list, n_id: str, af: str = 'ipv4', *,
                      vrf: str = 'default', activate: str = '',
                      **kwargs: typing.Any) -> str:
  a = activate or af
  cmd = _AF_SUMMARY.get(a, _AF_SUMMARY['ipv4'])
  if vrf != 'default' and a == 'ipv4':
    cmd = f'show ip bgp vrf {vrf} summary'
  return cmd


def valid_bgp_neighbor(ngb: list, n_id: str, af: str = 'ipv4', *,
                       vrf: str = 'default', state: str = 'Established',
                       activate: str = '', intf: str = '',
                       **kwargs: typing.Any) -> str:
  text = _text(global_vars.get_result_dict('_result'))
  a = activate or af
  n_addr = _common.get_bgp_neighbor_id(ngb, n_id, a)
  if n_addr is True:                                       # unnumbered EBGP peer
    if not intf:
      raise Exception('Need an interface name for an unnumbered BGP neighbor')
    n_addr = intf
  if not n_addr:
    raise Exception(f'Cannot find the {a} address of BGP neighbor {n_id}')

  # OcNOS summary rows: "<peer>  4  <as> ... <up/down>  <State/PfxRcd>"
  # Established -> the last column is a numeric prefix count; otherwise it is
  # a text state (Idle/Active/Connect/OpenSent...).
  row = None
  for ln in text.splitlines():
    toks = ln.split()
    if toks and toks[0] == str(n_addr):
      row = toks
      break

  established = row is not None and _row_established(row)

  if state == 'missing':
    if not established:
      return f'BGP neighbor {n_addr} ({n_id}) is correctly not Established'
    raise Exception(f'Unexpected established BGP neighbor {n_addr} ({n_id})')

  if row is None:
    raise Exception(f'The router has no BGP neighbor {n_addr} ({n_id}) in address family {a}')
  if not established:
    raise Exception(f'BGP neighbor {n_addr} ({n_id}) is not Established (row: {" ".join(row)})')
  return f'BGP neighbor {n_addr} ({n_id}) is Established'


def ansible_bgp_prefix(pfx: str, af: str = 'ipv4', vrf: str = 'default',
                    **kwargs: typing.Any) -> str:
  cmd = _AF_TABLE.get(af, _AF_TABLE['ipv4'])
  if vrf != 'default' and af == 'ipv4':
    cmd = f'show ip bgp vrf {vrf}'
  return cmd


def valid_bgp_prefix(pfx: str, af: str = 'ipv4', vrf: str = 'default',
                     state: str = 'present', **kwargs: typing.Any) -> str:
  text = _text(global_vars.get_result_dict('_result'))
  pfx = pfx if isinstance(pfx, str) else str(pfx)
  # A prefix may be printed with or without its mask in the BGP table; match the
  # network portion so 172.42.42.0/24 also matches a "172.42.42.0" table entry.
  net = pfx.split('/')[0]
  seen = any(net in ln for ln in text.splitlines())
  if state in ('missing', 'absent'):
    if seen:
      raise Exception(f'Prefix {pfx} unexpectedly present in the BGP table')
    return f'Prefix {pfx} is correctly absent from the BGP table'
  if not seen:
    raise Exception(f'Prefix {pfx} is not in the BGP table')
  return f'Prefix {pfx} is in the BGP table'
