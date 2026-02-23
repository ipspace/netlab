#
# Juniper cRPD quirks
#
from box import Box

from . import _Quirks


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
