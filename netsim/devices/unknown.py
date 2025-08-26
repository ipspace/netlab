#
# Arista EOS quirks
#
from box import Box

from ..utils import log
from . import _Quirks

'''
Check whether the 'unknown' device has clab kind (cannot use 'unknown', that would annoy clab)
'''
def check_clab_device_kind(node: Box, topology: Box) -> None:
  if topology.provider != 'clab' and node.get('provider') != 'clab':
    return
  
  if not 'kind' in node.get('clab',{}):
    log.error(
      f'Unknown device {node.name} using containerlab provider must have clab.kind defined',log.MissingValue)

class Unknown(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    unprovisioned_group = topology.groups.unprovisioned
    if not 'members' in unprovisioned_group:
      unprovisioned_group.members = []

    if not node.name in unprovisioned_group.members:
        unprovisioned_group.members.append(node.name)

    check_clab_device_kind(node, topology)