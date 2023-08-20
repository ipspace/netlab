#
# First-hop gateway transformation module
#
import typing
from box import Box

from . import _Module,get_effective_module_attribute
from ..utils import log, strings
from .. import data
from ..augment.nodes import reserve_id
from ..augment import devices
from ..data.validate import validate_attributes,must_be_string

def check_gw_protocol(gw: Box, path: str, topology: Box) -> typing.Any:
  return must_be_string(
      parent=gw,
      key='protocol',
      path=path,
      module='gateway',
      valid_values=topology.defaults.gateway.attributes.protocols
    )

#
# Check whether a node supports all FHRP protocols configured on it
#

def check_protocol_support(node: Box, topology: Box) -> bool:
  features = devices.get_device_features(node,topology.defaults)
  proto_list = []
  OK = True

  for intf in node.interfaces:                                        # Iterate over interfaces
    if not 'gateway' in intf:                                         # ... and skip interfaces without FHRP
      continue
    gw_proto = intf.gateway.protocol                                  # We're asuming someone else did a sanity check on this value
    if gw_proto in proto_list:                                        # Already checked?
      continue

    proto_list.append(gw_proto)
    if not gw_proto in features.gateway.protocol:
      OK = False
      log.error(
        f'Node {node.name} ({node.device}) does not support gateway protocol {gw_proto}',
        log.IncorrectValue,
        'gateway')

  return OK

#
# Remove unicast IPv4 addresses from interfaces that use 'anycast' gateway protocol
# and have 'gateway.anycast.unicast' set to False
#
def cleanup_unicast_ip(node: Box) -> None:
  for intf in node.interfaces:
    if not intf.get('gateway',False):                       # This interface not using FHRP or FHRP is disabled
      continue

    if intf.gateway.protocol != 'anycast':                  # Leave non-anycast FHRP implementations alone, they need node IP addresses
      continue

    if intf.get('gateway.anycast.unicast',None) is False:   # Are we forbidden to use unicast IP addresses together with anycast ones?
      intf.pop('ipv4',None)                                 # No unicast with anycast ==> pop the address

#
# Default settings copied onto individual links have parameters for every known FHRP protocol.
# We don't need those parameters on every interface -- this function cleans up unusud gateway protocol
# parameters from interfaces and returns a list of active protocols so we know what to clean on the
# node level.

def cleanup_protocol_parameters(node: Box,topology: Box) -> list:
  active_proto: list = []

  proto_list = topology.defaults.gateway.attributes.protocols         # List of known FHRP protocols
  for intf in node.interfaces:                                        # Iterate over interfaces
    if not 'gateway' in intf:                                         # ... and skip interfaces without FHRP
      continue

    gw_proto = intf.gateway.protocol                                  # We're asuming someone else did a sanity check on this value
    if not gw_proto in active_proto:                                  # Add the current protocol to the list of active protocols
      active_proto.append(gw_proto)

    for k in list(intf.gateway):                                      # Now iterate over all keywords in interface gateway settings
      if k != gw_proto and k in proto_list:                           # ... found FHRP protocol that is NOT the active protocol
        intf.gateway.pop(k,None)                                      # ... useless, pop it

  return active_proto

class FHRP(_Module):

  def module_init(self, topology: Box) -> None:
    gw = data.get_global_settings(topology,'gateway')
    if not gw or gw is None:
      log.error(
        f'Global/default gateway parameters are missing. We need at least a gateway ID',
        log.IncorrectType,
        'gateway')
      return

    check_gw_protocol(gw,'topology.gateway',topology)

    if not data.is_true_int(gw.id):
      log.error(
        f'Global/default gateway.id parameter is missing or not integer',
        log.IncorrectType,
        'gateway')
      return

    if gw.id > 0:
      reserve_id(gw.id)

  def link_pre_link_transform(self, link: Box, topology: Box) -> None:
    if not 'gateway' in link:
      return

    global_gateway = data.get_global_settings(topology,'gateway')
    if not global_gateway:                      # pragma: no cover
      return                                    # We know (from init) that we have global parameters. This is just to keep mypy happy

    if link.gateway is True:                    # We just want to do FHRP on the link ==> take global parameters
      link.gateway = global_gateway
    elif link.gateway is False:                 # We DEFINITELY don't want FHRP on this link ==> remove it and move on
      link.pop('gateway',None)
      return
    else:                                       # Otherwise merge global defaults with links settings (because we usually don't do that)
      check_gw_protocol(link.gateway,f'{link._linkname}',topology)
      link.gateway = global_gateway + link.gateway

    for k in ('id','protocol'):
      if not k in link.gateway or not link.gateway[k]:
        log.error(
          f'Gateway attribute {k} is missing in {link._linkname}\n' + \
          strings.extra_data_printout(strings.format_structured_dict(link)),
          log.MissingValue,
          'gateway')
        return

    if not data.is_true_int(link.gateway.id):
      log.error(
        f'Gateway.id parameter in {link._linkname} must be an integer\n' + \
          strings.extra_data_printout(strings.format_structured_dict(link)),
        log.IncorrectType,
        'gateway')
      return

    if link.gateway.id == -1:
        log.error(
          f'Cannot use -1 as the gateway ID in {link._linkname} -- that would be the broadcast address\n' + \
          strings.extra_data_printout(strings.format_structured_dict(link)),
          log.IncorrectValue,
          'gateway')

  def node_post_transform(self, node: Box, topology: Box) -> None:
    if not check_protocol_support(node,topology):
      return

    cleanup_unicast_ip(node)
    active_proto = cleanup_protocol_parameters(node,topology)         # Cleanup interface parameters and get a list of active protocols
    if 'gateway' in node:
      for k in list(node.gateway):                                    # Iterate over node-level gateway parameters
        if not k in active_proto:                                     # Not a parameter for a FHRP active on this node?
          node.gateway.pop(k,None)                                    # ... zap it!
