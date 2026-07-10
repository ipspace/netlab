"""
Top-level Arista EOS validation plugin

Import BGP checks
"""

from netsim.utils import routing as _rp_utils
from netsim.validate.bgp.eos import *
from netsim.validate.ospf.eos import *


def exec_ping(
      host: str,
      src: typing.Optional[str] = None,
      af: typing.Optional[str] = None,
      count: int = 5,
      pkt_len: typing.Optional[int] = None,
      **kwargs: typing.Any) -> str:

  if pkt_len is not None and pkt_len < 64:
    raise Exception('Minimum IP packet size for ping plugin is 64 bytes')

  host = _rp_utils.try_intf_address(host)
  cmd = 'enable\nping ' + ('ip' if af is None or af == 'ipv4' else af) + ' ' + host
  if src:
    cmd += f' source {_rp_utils.try_intf_address(src)}'

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

  msg = f'Ping to {af + " " if af else ""}{_rp_utils.try_intf_address(host)}'
  if src:
    msg += f' from {_rp_utils.try_intf_address(host)}'
  if pkt_len:
    msg += f' size {pkt_len}'

  if expect == 'fail':
    for kw in ("0 packets received","0 received","unreachable"):
      if kw in _result.stdout:
        return msg+' failed as expected'
    raise Exception(msg+' did not fail')
  else:
    if pkt_len:
      pkt_exp = pkt_len - (40 if af == 'ipv6' else 20)
      OK_result = f"{ pkt_exp } bytes from"
    else:
      OK_result = " bytes from"
    if OK_result in _result.stdout:
      return msg+' succeeded'
    raise Exception(msg+' failed')
