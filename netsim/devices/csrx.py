#
# Juniper cSRX quirks
#
from box import Box

from ..utils import log
from . import _Quirks


def csrx_port_num(node: Box) -> None:
  if_count = len(node.get('interfaces', []))
  node.clab.env.CSRX_PORT_NUM = if_count + 1 # +1 for the management interface
  if if_count > 16:
    log.error(
      f'cSRX supports a maximum of 16 interfaces. Node {node.name} has {if_count} interfaces.',
      category=log.IncorrectValue,
      module=node.device)

class CSRX(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    csrx_port_num(node)
