"""
Top-level Arista EOS validation plugin

Import BGP checks
"""

from box import Box
from netsim.validate.bgp.eos import *
from netsim.validate.ospf.eos import *
from netsim.validate._common import get_address

def exec_ping(
      host: str,
      src: typing.Optional[str] = None,
      af: typing.Optional[str] = None,
      count: int = 5,
      pkt_len: typing.Optional[int] = None,
      **kwargs: typing.Any) -> str:

  host = get_address(host)
  cmd = 'enable\nping ' + ('ip' if af is None or af == 'ipv4' else af) + ' ' + host
  if src:
    cmd += f' source {get_address(src)}'

  if pkt_len:
    cmd += f' size {pkt_len}'

  if count:
    cmd += f' repeat {count}'

  return cmd

def valid_ping(
      host: str,
      src: typing.Optional[str] = None,
      af: typing.Optional[str] = None,
      count: int = 5,
      pkt_len: typing.Optional[int] = None,
      expect: typing.Optional[str] = None) -> str:
  _result = global_vars.get_result_dict('_result')

  msg = f'Ping to {af + " " if af else ""}{get_address(host)}'
  if src:
    msg += f' from {get_address(src)}'
  if pkt_len:
    msg += f' size {pkt_len}'

  if expect == 'fail':
    for kw in ("0 packets received","0 received","unreachable"):
      if kw in _result.stdout:
        return msg+' failed as expected'
    raise Exception(msg+' did not fail')
  else:
    if f"{ pkt_len + 8 if pkt_len else 80 } bytes from" in _result.stdout:
      return msg+' succeeded'
    raise Exception(msg+' failed')
