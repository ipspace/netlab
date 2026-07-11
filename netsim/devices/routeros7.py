#
# Mikrotik RouterOS7 quirks
#
from box import Box

from ..utils import log
from ..utils import routing as _routing
from . import _common, _Quirks, report_quirk


def check_vpnv6_af(node: Box, topology: Box) -> None:
  '''
  VPNv6 does not work on RouterOS7
  '''
  for ngb in node.get('bgp.neighbors',[]):
    if 'vpnv6' in ngb:
      report_quirk(
        f'We could not get VPNv6 AF to work on Mikrotik RouterOS7 (node {node.name})',
        node=node,
        quirk='vpnv6',
        category=log.IncorrectValue,
        module='quirks')
      return

def build_afi_lists(node: Box) -> None:
  '''
  Adding AFIs to RouterOS7 BGP connections is non-trivial. This helper function
  builds per-transport-connection AFI lists that can be used directly in the
  configuration templates.

  Please note that the AFI lists are built only for global BGP neighbors. The
  VRF BGP neighbors use only the "native" AF.
  '''
  for ngb in _routing.neighbors(node,vrf=False):
    for t_af in ['ipv4','ipv6']:                              # Iterate over potential transport AFs
      if t_af not in ngb:                                     # Neighbor not using this AF? I'm fine with that...
        continue
      ngb._afi_list[t_af] = []
      if 'activate' not in ngb or ngb.activate.get(t_af,False):
        ngb._afi_list[t_af].append(t_af)                      # Append default AF if needed
      for bgp_af in ['vpnv4','vpnv6','evpn']:                 # Then append service AFs
        if bgp_af in ngb and (ngb[bgp_af] == ngb[t_af] or ngb[bgp_af] == t_af):
          ngb._afi_list[t_af].append(bgp_af)

class RouterOS7(_Quirks):
  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    if node.get('mpls.vpn',False):
      check_vpnv6_af(node,topology)
    _common.check_tagged_vlan_1(node)
    if node.get('bgp.neighbors'):
      build_afi_lists(node)
