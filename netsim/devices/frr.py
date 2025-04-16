#
# FRR quirks
#
from box import Box

from . import _Quirks,report_quirk
from ..utils import log

"""
Because FRR uses a 'bridge per VLAN' model, STP BPDUs are sent as tagged packets, not untagged.
This makes FRR incompatible with STP in a VLAN trunking scenario, as its peers expect standard 
STP BPDUs to be sent untagged
"""
def check_stp_on_trunks(node: Box, topology: Box) -> None:
  err_data = []
  for intf in node.interfaces:
    if intf.type=='vlan_member':
      err_data.append(f'Interface {intf.ifname}')

  if err_data:
    report_quirk(
      f'FRR node {node.name} runs STP per VLAN, it sends tagged standard STP BDPUs which is incompatible',
      quirk='stp_on_trunks',
      more_data=err_data,
      node=node)

"""
FRR supports the deleting of communities, but only through community lists.
This method creates such named lists for any policies that delete communities
"""
def create_bgp_community_delete_lists(node: Box) -> None:
  for policy,entries in node.get('routing.policy',{}).items():
    for e in entries:
      if not e.get('set.community.delete',False):
        continue
      for type in ['standard','large','extended']:
        if type not in e.set.community:
          continue
        cname = f"DEL_{ policy }_{ e.sequence }"
        values = [ { 'type': type, 'action': 'permit', '_value': i } for i in e.set.community[type] ]
        node.routing.community[ cname ] = { 'type': type, 'action': 'permit', 'value': values }
        e.set.community.pop( type, None )
        e.set.community._frr_list = cname

class FRR(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    if 'stp' in mods:
      if log.debug_active('quirks'):
        print(f'FRR: Checking STP for {node.name}')
      check_stp_on_trunks(node,topology)
    if 'routing' in mods:
      create_bgp_community_delete_lists(node)
