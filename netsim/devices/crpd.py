#
# Juniper cRPD quirks
#
from box import Box

from ..utils import log
from . import _Quirks, report_quirk


def vrf_route_leaking(node: Box) -> None:
  for vname,vdata in node.get('vrfs',{}).items():
    if '_leaked_routes' in vdata:
      report_quirk(
        text=f'Inter-VRF route leaking does not work on cRPD (node {node.name} vrf {vname})',
        node=node,
        category=log.IncorrectValue)

class CRPD(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    from . import junos

    junos.check_multiple_loopbacks(node,topology)
    junos.check_evpn_ebgp(node,topology)
    junos.policy_aspath_quirks(node,topology)
    junos.as_prepend_quirk(node,topology)
    junos.large_community_list_quirk(node,topology)
    junos.community_set_quirk(node,topology)
    junos.default_originate_check(node,topology)
    junos.build_bgp_import_export_policy_chain(node,topology)
    vrf_route_leaking(node)
