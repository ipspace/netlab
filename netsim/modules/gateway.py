#
# First-hop gateway transformation module
#
from box import Box

from . import _Module,get_effective_module_attribute
from .. import common
from .. import data
from ..augment.nodes import reserve_id
from ..data.validate import validate_attributes

class FHRP(_Module):

  def module_init(self, topology: Box) -> None:
    gw = data.get_global_parameter(topology,'gateway')
    if not gw or gw is None:
      common.error(
        f'Global/default gateway parameters are missing. We need at least a gateway ID',
        common.IncorrectType,
        'gateway')
      return

    if not data.is_true_int(gw.id):
      common.error(
        f'Global/default gateway.id parameter is missing or not integer',
        common.IncorrectType,
        'gateway')
      return

    if gw.id > 0:
      reserve_id(gw.id)

  def link_pre_link_transform(self, link: Box, topology: Box) -> None:
    if not 'gateway' in link:
      return

    global_gateway = data.get_global_parameter(topology,'gateway')
    if not global_gateway:                      # pragma: no cover
      return                                    # We know (from init) that we have global parameters. This is just to keep mypy happy

    if link.gateway is True:                    # We just want to do FHRP on the link ==> take global parameters
      link.gateway = global_gateway
    elif link.gateway is False:                 # We DEFINITELY don't want FHRP on this link ==> remove it and move on
      link.pop('gateway',None)
    else:                                       # Otherwise merge global defaults with links settings (because we usually don't do that)
      link.gateway = global_gateway + link.gateway

    for k in ('id','protocol'):
      if not k in link.gateway or not link.gateway[k]:
        common.error(
          f'Gateway attribute {k} is missing in links[{link.linkindex}]\n' + \
          common.extra_data_printout(common.format_structured_dict(link)),
          common.MissingValue,
          'gateway')
        return

    if not data.is_true_int(link.gateway.id):
      common.error(
        f'Gateway.id parameter in links[{link.linkindex}] must be an integer\n' + \
          common.extra_data_printout(common.format_structured_dict(link)),
        common.IncorrectType,
        'gateway')
      return

    if link.gateway.id == -1:
        common.error(
          f'Cannot use -1 as the gateway ID in links[{link.linkindex}] -- that would be the broadcast address\n' + \
          common.extra_data_printout(common.format_structured_dict(link)),
          common.IncorrectValue,
          'gateway')

  def node_post_transform(self, node: Box, topology: Box) -> None:
    for intf in node.interfaces:                                      # Time to clean up interface addresses
      if not intf.get('gateway',False):                               # This interface not using FHRP or FHRP is disabled
        continue

      if intf.gateway.protocol != 'anycast':                          # Leave non-anycast FHRP implementations alone, they need node IP addresses
        continue

      if data.get_from_box(intf,'gateway.anycast.unicast'):           # Do we use unicast IP addresses together with anycast ones?
        continue

      intf.pop('ipv4',None)                                           # No unicast with anycast ==> pop the address
