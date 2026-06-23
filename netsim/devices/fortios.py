#
# FortiOS quirks
#
from box import Box

from ..utils import log
from ..utils import routing as _routing
from . import _Quirks
from ._common import check_indirect_static_routes


def check_bgp_gr_restart_time(node: Box) -> None:
  for rp_data,_,vname in _routing.rp_data(node,'bgp'):
    if rp_data.get('gr.restart_time',None) != 0:
      continue

    vrf_info = f' in VRF {vname}' if vname else ''
    log.error(
      f'FortiOS does not support bgp.gr.restart_time value 0{vrf_info} on node {node.name}',
      log.IncorrectValue,
      'fortios')


class FortiOS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    check_indirect_static_routes(node)
    check_bgp_gr_restart_time(node)
