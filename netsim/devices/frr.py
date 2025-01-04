#
# FRR quirks
#
from box import Box

from . import _Quirks,report_quirk
from ..utils import log

"""
Because FRR uses a 'bridge per VLAN' model, STP BPDUs are sent as tagged packets, not untagged.
This makes FRR incompatible with basic STP in a VLAN trunking scenario
"""
def check_stp_on_trunks(node: Box, topology: Box) -> None:
  if node.get('stp.protocol',"stp")=="stp":     # Are we being asked to run standard STP with untagged BPDUs?
    err_data = []
    for intf in node.interfaces:
      if intf.type=='vlan_member':
        err_data.append(f'Interface {intf.ifname}')

    if err_data:
      report_quirk(
        f'FRR node {node.name} runs STP per VLAN, it cannot run regular untagged STP on VLAN trunks',
        quirk='stp_on_trunks',
        more_data=err_data,
        node=node)

class FRR(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    if 'stp' in mods:
      if log.debug_active('quirks'):
        print(f'FRR: Checking STP for {node.name}')
      check_stp_on_trunks(node,topology)