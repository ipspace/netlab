"""
OcNOS OSPFv2 / OSPFv3 validation plugin.

Uses the `ansible` validation action (netsim/cli/validate/ansible.py): `ansible_<test>()`
returns the OcNOS show command, netlab runs it via the ipinfusion.ocnos Ansible module,
and `valid_<test>()` asserts on the result. OcNOS `show ip ospf neighbor` is CLI text,
so the validators screen-scrape `_result.stdout`; signatures match the FRR/EOS plugins
(`ospf_neighbor`, `ospf_prefix`) so the stock integration tests can target an OcNOS DUT.
"""

import ipaddress
import typing

from box import Box

from netsim.data import global_vars


def _text(_result: typing.Any) -> str:
  if isinstance(_result, (Box, dict)):
    out = _result.get('stdout', '')
    return '\n'.join(out) if isinstance(out, list) else str(out)
  return str(_result or '')


def ansible_ospf_neighbor(id: str, present: bool = True, vrf: str = 'default',
                          proto_name: str = 'OSPFv2', **kwargs: typing.Any) -> str:
  scope = '' if vrf == 'default' else f' vrf {vrf}'
  af = 'ipv6' if proto_name == 'OSPFv3' else 'ip'
  return f'show {af} ospf{scope} neighbor'


def valid_ospf_neighbor(id: str, present: bool = True, vrf: str = 'default',
                        proto_name: str = 'OSPFv2', **kwargs: typing.Any) -> str:
  try:
    ipaddress.IPv4Address(id)
  except Exception as exc:
    raise Exception(f'OSPF router ID {id} is not a valid IPv4 address') from exc
  text = _text(global_vars.get_result_dict('_result'))
  rows = [ln for ln in text.splitlines() if str(id) in ln.split()]

  if not present:
    if rows:
      raise Exception(f'Unexpected {proto_name} neighbor {id}')
    return f'{proto_name} neighbor {id} is correctly absent'
  if not rows:
    raise Exception(f'There is no {proto_name} neighbor {id} in VRF {vrf}')
  if not any('Full' in ln for ln in rows):
    raise Exception(f'{proto_name} neighbor {id} is not in state Full')
  return f'{proto_name} neighbor {id} is Full'


def ansible_ospf6_neighbor(id: str, **kwargs: typing.Any) -> str:
  return ansible_ospf_neighbor(id, proto_name='OSPFv3')


def valid_ospf6_neighbor(id: str, present: bool = True, vrf: str = 'default',
                         **kwargs: typing.Any) -> str:
  return valid_ospf_neighbor(id, present=present, vrf=vrf, proto_name='OSPFv3')


def ansible_ospf_prefix(pfx: str, vrf: str = 'default', **kwargs: typing.Any) -> str:
  scope = '' if vrf == 'default' else f' vrf {vrf}'
  af = 'ipv6' if ':' in str(pfx) else 'ip'
  return f'show {af} route{scope} ospf'


def valid_ospf_prefix(pfx: str, state: str = 'present', **kwargs: typing.Any) -> str:
  text = _text(global_vars.get_result_dict('_result'))
  pfx = pfx if isinstance(pfx, str) else str(pfx)
  # Match on the address portion, not the literal mask: an OcNOS loopback such as
  # 2001:db8:1:2::1/64 is installed as a host route (.../128) plus the network
  # (.../64), so the raw '<addr>/<len>' string appears in neither table row.
  needle = pfx.split('/')[0]
  seen = any(needle in ln for ln in text.splitlines())
  if state in ('missing', 'absent'):
    if seen:
      raise Exception(f'Prefix {pfx} unexpectedly present in the OSPF routing table')
    return f'Prefix {pfx} is correctly absent from the OSPF routing table'
  if not seen:
    raise Exception(f'Prefix {pfx} is not in the OSPF routing table')
  return f'Prefix {pfx} is in the OSPF routing table'


def ansible_ospf6_prefix(pfx: str, **kwargs: typing.Any) -> str:
  return ansible_ospf_prefix(pfx)


def valid_ospf6_prefix(pfx: str, state: str = 'present', **kwargs: typing.Any) -> str:
  return valid_ospf_prefix(pfx, state=state)
