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

def cleanup_intf_protocol_parameters(node: Box,topology: Box) -> list:
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
      elif k in node.get('gateway'):                                  # Do we have node-level parameters for this protocol?
        intf.gateway[k] = node.gateway[k] + intf.gateway[k]           # ... copy them to all interfaces

  return active_proto

'''
Process a gateway ID found somewhere in the data structures.
'''
def process_gw_id(
      gw_id: typing.Optional[int] = None,
      required: bool = False,
      path: str = 'Global/default') -> None:

  if gw_id is None:
    if not required:
      return
    log.error(f'{path} gateway.id parameter is missing',log.MissingValue,'gateway')
    return
  
  if not data.is_true_int(gw_id):
    log.error(f'{path} gateway.id parameter is not integer',log.IncorrectValue,'gateway')
    return
  
  if gw_id < 0:
    return
  
  reserve_id(gw_id)

class FHRP(_Module):

  '''
  The main job of the module_init routine is to find potential low-value
  gateway.ids and reserve those IDs before they can be used for nodes.

  At this point, the data validation and other sanity checks were not done yet,
  so we have to be extra-careful accessing the data structures.
  '''
  def module_init(self, topology: Box) -> None:
    gw = data.get_global_settings(topology,'gateway')
    if not gw or gw is None:
      log.error(
        f'Global/default gateway parameters are missing. We need at least a gateway ID',
        log.IncorrectType,
        'gateway')
      return

    check_gw_protocol(gw,'topology.gateway',topology)

    process_gw_id(gw.get('id',None),required=True)          # Process global GW ID

    for link in topology.links:                             # Iterate over links
      if not isinstance(link,Box):                          # A link should be a Box by this time, but who knows...
        continue

      # Check the link gateway ID. If it doesn't exist, get returns None, and the function
      # returns immediately (no error is reported due to required == False).
      #
      process_gw_id(link.get('gateway.id',None),required=False,path=f'Link {link._linkname}')

    vlans = topology.get('vlans',None)                    # We might have global VLAN definitions
    if isinstance(vlans,Box):                             # If we do and the data looks sane
      for vname,vdata in vlans.items():                   # ... iterate over VLAN definitions
        if not isinstance(vdata,Box):                     # ... skipping data that makes no sense (not a Box)
          continue

        # Process VLAN GW ID like you would a link gateway ID
        #
        process_gw_id(vdata.get('gateway.id',None),required=False,path=f'VLAN {vname}')

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
    active_proto = cleanup_intf_protocol_parameters(node,topology)    # Cleanup interface parameters and get a list of active protocols
    if 'gateway' in node:
      for k in list(node.gateway):                                    # Iterate over node-level gateway parameters
        if not k in active_proto:                                     # Not a parameter for a FHRP active on this node?
          node.gateway.pop(k,None)                                    # ... zap it!
