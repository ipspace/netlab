"""
OcNOS IS-IS validation via the `ansible` validation action (netsim/cli/validate/ansible.py).

`ansible_<test>()` returns the OcNOS show command, netlab runs it through the
ipinfusion.ocnos Ansible module, and `valid_<test>()` asserts on the CLI text.
Signatures mirror netsim/validate/isis/frr.py. Note: OcNOS `show isis neighbor`
trips the ipinfusion.ocnos.ocnos_command module (like `show route-map` / `ping`),
so we read adjacencies from `show clns neighbors`, whose rows carry the neighbor
hostname, state and level (Type = L1/L2/L1L2); this needs isis dynamic-hostname.
"""

import typing

from box import Box

from netsim.data import global_vars


def _text(_result: typing.Any) -> str:
  if isinstance(_result, (Box, dict)):
    out = _result.get('stdout', '')
    return '\n'.join(out) if isinstance(out, list) else str(out)
  return str(_result or '')


def ansible_isis_neighbor(id: str, **kwargs: typing.Any) -> str:
  return 'show clns neighbors'


def valid_isis_neighbor(id: str, present: bool = True, state: str = 'Up',
                        level: str = '', area: str = '') -> str:
  text = _text(global_vars.get_result_dict('_result'))
  # `show clns neighbors` rows:
  #   System Id   Interface   SNPA   State   Holdtime   Type   Protocol
  #   x1          eth1        ...    Up      27         L1     IS-IS
  rows = [ln for ln in text.splitlines() if id in ln.split()]

  if not present:
    if rows:
      raise Exception(f'Unexpected IS-IS neighbor {id}')
    return f'IS-IS neighbor {id} is correctly absent'

  if not rows:
    raise Exception(f'There is no IS-IS neighbor {id}')
  if not any(state in ln.split() for ln in rows):
    raise Exception(f'IS-IS neighbor {id} is not in state {state}')

  if level:
    # Type column carries L1 / L2 / L1L2; accept an L1 match inside L1L2 too.
    lv = level.upper()
    if not any(any(lv in tok.upper() for tok in ln.split()) for ln in rows):
      raise Exception(f'IS-IS neighbor {id} is not at level {level}')

  return f'IS-IS neighbor {id} is {state}' + (f' ({level})' if level else '')


def ansible_isis_prefix(pfx: str, level: str = '2', **kwargs: typing.Any) -> str:
  af = 'ipv6' if ':' in str(pfx) else 'ip'
  return f'show {af} route isis'


def valid_isis_prefix(pfx: str, level: str = '2', state: str = 'present',
                      **kwargs: typing.Any) -> str:
  text = _text(global_vars.get_result_dict('_result'))
  pfx = pfx if isinstance(pfx, str) else str(pfx)
  seen = any(pfx in ln for ln in text.splitlines())
  if state in ('missing', 'absent'):
    if seen:
      raise Exception(f'Prefix {pfx} unexpectedly present in the IS-IS routing table')
    return f'Prefix {pfx} is correctly absent from the IS-IS routing table'
  if not seen:
    raise Exception(f'Prefix {pfx} is not in the IS-IS routing table')
  return f'Prefix {pfx} is in the IS-IS routing table'
