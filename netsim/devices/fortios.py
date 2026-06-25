#
# FortiOS quirks
#
from box import Box

from ..data import removed_attributes
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


def check_ospf_gr(node: Box) -> None:
  """
  FortiOS drives OSPF graceful restart from a single 'set restart-mode graceful-restart'
  keyword per address family. That switch makes the device both a restarting router and a
  helper; the two roles cannot be configured independently. Reject the combinations the
  device cannot honour, leaving the restart role (which a helper rides along with) to render.
  """
  for o_data,_,vname in _routing.rp_data(node,'ospf'):
    gr = o_data.get('gr',None)
    restart_on = isinstance(gr,dict) and 'restart' in gr             # restart role explicitly enabled
    helper_on = isinstance(gr,dict) and 'helper' in gr               # helper role explicitly enabled
    helper_off = removed_attributes(o_data,'gr.helper')              # helper role explicitly disabled
    vrf_info = f' in VRF {vname}' if vname else ''

    if helper_on and not restart_on:                                 # Helper without restart: FortiOS would
      log.error(                                                     # ... have to make the restart promise too
        f'FortiOS cannot enable the OSPF graceful-restart helper role without restart '
        f'(set ospf.gr.restart) on node {node.name}{vrf_info}',
        log.IncorrectValue,
        'fortios')
    elif restart_on and helper_off:                                  # Restart with helper explicitly off:
      log.error(                                                     # ... the two roles share one switch
        f'FortiOS cannot enable OSPF graceful-restart restart while ospf.gr.helper is disabled '
        f'on node {node.name}{vrf_info}',
        log.IncorrectValue,
        'fortios')


class FortiOS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    check_indirect_static_routes(node)
    check_bgp_gr_restart_time(node)
    check_ospf_gr(node)
