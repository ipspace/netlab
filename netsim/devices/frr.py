#
# FRR quirks
#
from box import Box

from ..utils import log
from . import _Quirks, report_quirk

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

class FRR(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    if 'stp' in mods and node.get('stp.enable',True):
      if log.debug_active('quirks'):
        print(f'FRR: Checking STP for {node.name}')
      check_stp_on_trunks(node,topology)
