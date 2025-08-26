"""
FRR OSPFv2 validation routines
"""

import re
import typing

from netsim.data import global_vars


def exec_ping(
      host: str,
      src: typing.Optional[str] = None,
      af: typing.Optional[str] = None,
      count: int = 5,
      pkt_len: typing.Optional[int] = None,
      expect: typing.Optional[str] = None) -> str:

  host = host.split('/')[0]
  cmd = f'ping -c {count} -W 1 -A'
  if af == 'ipv6':
    cmd += ' -6'
  elif af == 'ipv4':
    cmd += ' -4'
  if pkt_len:
    cmd += f' -s {pkt_len}'
  if src:
    cmd += ' -I '+src.split('/')[0]

  cmd += ' '+host
  cmd += ' || true'
  return cmd

'''
Extract the IP address the device tried to ping from the
result message and add it to the hostname if it differs from
the hostname used in validation request
'''
def extract_host(hostname: str, result: str) -> str:
  result_hdr = result.split(':')[0]                       # Get the initial 'PING X (A.B.C:D):' part
  if ':' not in result or hostname not in result_hdr:     # The hostname should be part of it, otherwise give up
    return hostname
  
  result_hdr = result_hdr.split(hostname)[1]              # Now get the part after the hostname
  if ')' not in result_hdr:                               # The hostname must have been an IP address
    return hostname                                       # ... or we would get an IP address in brackets
  
  M = re.search('\\([0-9a-fA-F:.]+\\)',result_hdr)
  return hostname + ' ' + M.group(0) if M else hostname

def valid_ping(
      host: str,
      src: typing.Optional[str] = None,
      af: typing.Optional[str] = None,
      count: int = 5,
      pkt_len: typing.Optional[int] = None,
      expect: typing.Optional[str] = None) -> str:
  _result = global_vars.get_result_dict('_result')

  host = extract_host(host.split('/')[0],_result.stdout)
  msg = f'Ping to {af + " " if af else ""}{host}'
  if src:
    msg += f' from {src}'
  if pkt_len:
    msg += f' size {pkt_len}'

  if expect == 'fail':
    for kw in ("0 packets received","0 received","unreachable"):
      if kw in _result.stdout:
        return msg+' failed as expected'
    raise Exception(msg+' did not fail')
  else:
    if f"{ pkt_len + 8 if pkt_len else 64 } bytes from" in _result.stdout:
      return msg+' succeeded'
    raise Exception(msg+' failed')

def exec_default6() -> str:
  return 'ip -6 route list default'

def valid_default6() -> str:
  _result = global_vars.get_result_dict('_result')
  if 'default' in _result.stdout:
    return 'IPv6 default route is present'
  
  raise Exception('IPv6 default route is missing')

def exec_route(pfx: str, af: str = 'ipv4', intf: str = '', state: str = '') -> str:
  cmd = 'ip -6 route' if af == 'ipv6' else 'ip route'
  cmd += f' | grep "{pfx}"'
  if intf:
    cmd += f' | grep "dev {intf}"'

  return cmd

def valid_route(pfx: str, af: str = 'ipv4', intf: str = '', state: str = '') -> str:
  _result = global_vars.get_result_dict('_result')

  miss_msg = f'{af} route {pfx} is not in the routing table' + (f' or does not point to {intf}' if intf else '')
  if state == 'missing':
    if not _result.stdout:
      return miss_msg
    raise Exception(f'{af} {pfx} should not be in the routing table')
  
  if _result.stdout:
    return f'{af} route {pfx} ' + (f'points to {intf}' if intf else 'is in the routing table')
  raise Exception(miss_msg)
