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
  for o_data,_,vname in _routing.rp_data(node,'ospf'):
    gr = o_data.get('gr',None)
    if not isinstance(gr,dict):
      continue

    restart_on = 'restart' in gr
    helper_on = 'helper' in gr
    helper_off = removed_attributes(o_data,'gr.helper')
    vrf_info = f' in VRF {vname}' if vname else ''

    # FortiOS has one OSPF GR switch. Restart implies helper on FortiOS,
    # but helper-only input must not enable forwarding-state preservation.
    if helper_on and not restart_on:
      log.error(
        f'FortiOS cannot enable the OSPF graceful-restart helper role without restart '
        f'(set ospf.gr.restart) on node {node.name}{vrf_info}',
        log.IncorrectValue,
        'fortios')
    elif restart_on and helper_off:
      log.error(
        f'FortiOS cannot enable OSPF graceful-restart restart while ospf.gr.helper is disabled '
        f'on node {node.name}{vrf_info}',
        log.IncorrectValue,
        'fortios')

    helper_data = gr.get('helper',{})
    if isinstance(helper_data,dict) and 'grace_period' in helper_data:
      log.warning(
        text=f'FortiOS cannot limit OSPF graceful-restart helper grace period on node {node.name}{vrf_info}',
        flag='gr_helper_grace',
        module='ospf')


class FortiOS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    check_indirect_static_routes(node)
    check_bgp_gr_restart_time(node)
    check_ospf_gr(node)
