#
# SRv6 transformation module
#

from box import Box

from ..augment import devices
from ..data import validate
from ..utils import log
from . import _Module, _routing


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
    sr_feature = devices.get_device_features(node,topology.defaults).get('sr',False)
    sr_attr = topology.defaults.sr.attributes
    _routing.node_proto_af(node,'sr',None)                  # Create node SR-MPLS AF if needed

    proto_af: set = set()                                   # Collect AFs supported by SR-MPLS protocols
    OK = True
    for sr_proto in node.sr.protocol:                       # Iterate over SR-MPLS protocols used on the node
      proto_info = sr_attr._proto_map[sr_proto]             # ... get protocol details
      if isinstance(sr_feature,Box) and \
         sr_proto not in sr_feature.protocol:               # Check whether the device supports the protocol
        log.error(
          f'Device {node.device} (node {node.name}) does not support {sr_proto} with SR-MPLS',
          category=log.IncorrectType,
          module='sr')
        OK = False
      elif proto_info.module not in node.module:            # ... and check that the node is using correct module(s)
        log.error(
          f'SR-MPLS on node {node.name} uses {sr_proto} without {proto_info.module} configuration module',
          category=log.MissingDependency,
          module='sr')
        OK = False
      else:
        proto_af.update(proto_info.af)                      # Add AFs supported by the SR-MPLS protocol

    if not OK:                                              # If we have protocol/support errors
      return                                                # ... it makes no sense to check the address families

    for af in log.AF_LIST:                                  # Find address families
      if af not in sr_data.af or af not in node.af:         # ... that are used on the node and enabled in sr.af
        continue
      if isinstance(sr_feature,Box) and 'af' in sr_feature: # Do we need to check AF support?
        if af not in sr_feature.af:
          log.error(
            f'Device {node.device} (node {node.name}) does not support SR-MPLS for {af}',
            category=log.IncorrectValue,
            module='sr')
          continue
      if af not in proto_af:
        log.error(
          f'{af} address family is not supported by the SR-MPLS protocol(s) {node.sr.protocol} used on {node.name}',
          category=log.MissingDependency,
          module='sr')
        continue
      if af not in sr_data.node_sid:                        # Is node SID statically defined (or empty)?
        af_offset = topology.get(f'sr.node_sid_offset.{af}',100 if af == 'ipv6' else 0)
        node.sr.node_sid[af] = node.id + af_offset          # Set node SID to node ID plus AF offset
