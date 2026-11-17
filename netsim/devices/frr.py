#
# FRR quirks
#
from box import Box

from ..augment import devices as a_devices
from ..utils import log
from . import _Quirks, report_quirk
from .linux import etc_resolv_mapping

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
Containerlab 'frr' kind enables all FRR daemons unless the node has a 'daemons' list. Build
that list from the daemons needed by netlab modules and the frr.daemons node attribute.

'zebra' is always in the list: it's always started anyway, and an empty list would enable all
daemons. frr.daemons set to True enables all daemons (no 'daemons' list)
"""
def set_clab_daemons(node: Box, topology: Box) -> None:
  if node.get('clab.kind',None) != 'frr':
    return
  extra = node.get('frr.daemons',[])
  if extra is True:
    return

  mod_daemons = a_devices.get_device_attribute(node,'group_vars.netlab_frr_daemons',topology.defaults) or {}
  daemons = ['zebra']
  for m in node.get('module',[]):
    daemons.extend(mod_daemons.get(m,[]))
  if isinstance(extra,list):
    daemons.extend(extra)
  node.clab.daemons = list(dict.fromkeys(daemons))

class FRR(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    etc_resolv_mapping(node,topology)
    set_clab_daemons(node,topology)
    mods = node.get('module',[])
    if 'stp' in mods and node.get('stp.enable',True):
      if log.debug_active('quirks'):
        print(f'FRR: Checking STP for {node.name}')
      check_stp_on_trunks(node,topology)
