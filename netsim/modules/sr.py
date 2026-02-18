#
# SRv6 transformation module
#

from box import Box

from ..data import validate
from ..utils import log
from . import _Module


class SR(_Module):
  def pre_default(self, topology: Box) -> None:
    if 'sr' not in topology:
      return
    validate.legacy_attributes(
      t_object=topology,
      topology=topology,
      o_path=f'',
      module='sr',
      attr_namespace='global')

  def node_pre_default(self, node: Box, topology: Box) -> None:
    if 'sr' not in node:
      return
    validate.legacy_attributes(
      t_object=node,
      topology=topology,
      o_path=f'nodes.{node.name}',
      module='sr',
      attr_namespace='node')

  def node_post_transform(self, node: Box, topology: Box) -> None:
    sr_data = node.sr                                       # Note: this will create node.sr dictionary if needed
    for af in log.AF_LIST:                                  # Find active address families
      if af not in node.af:
        continue
      if af not in sr_data.node_sid:                        #  Is node SID statically defined (or empty)?
        af_offset = topology.get(f'sr.node_sid_offset.{af}',100 if af == 'ipv6' else 0)
        node.sr.node_sid[af] = node.id + af_offset          # Set node SID to node ID plus AF offset
