"""
Utility functions for the routing module
"""

from box import Box

from ...data import append_to_list, get_empty_box
from ...utils import log


def eval_prefixset(pfx: str, path: str, topology: Box) -> dict:
  """
  Evaluate a generic routing prefix into a dictionary of ipv4/ipv6 prefix lists
  """

  def link_list_prefix(link_list: list) -> Box:
    """
    Extract all address information from a list of links into the final result
    """
    result = get_empty_box()
    for link in link_list:
      if 'prefix' not in link:
        continue
      for af in log.AF_LIST:
        if af in link.prefix:
          append_to_list(result,af,link.prefix[af])

    return result

  result = get_empty_box()
  if ':' in pfx:
    return {'ipv6': pfx}
  if pfx.count('.') > 1:
    return {'ipv4': pfx}

  if '.' in pfx:
    (pfx_type,pfx) = pfx.split('.',1)
  else:
    pfx_type = 'prefix'

  if pfx_type == 'prefix':
    pfx_data = topology.get(f'prefix.{pfx}',None)
    if pfx_data is None:
      log.error(
        f'Invalid named prefix {pfx} specified in {path}',category=log.IncorrectValue,module='routing')
      return {}
    if not pfx_data:
      log.error(
        f'Named prefix {pfx} used in {path} has no IPv4/IPv6 information',category=log.MissingValue,module='routing')
      return {}
    return pfx_data

  if pfx_type == 'vlans':
    pfx_data = topology.get(f'vlans.{pfx}',None)
    if pfx_data is None:
      log.error(
        f'Invalid global VLAN {pfx} specified in {path}',category=log.IncorrectValue,module='routing')
      return {}
    if 'prefix' not in pfx_data:
      log.error(
        f'VLAN {pfx} used in {path} has no prefix information',category=log.MissingValue,module='routing')
      return {}
    else:
      return pfx_data.prefix      

  if pfx_type == 'links':
    link_list = [ lnk for lnk in topology.links if lnk.get('linkid',None) == pfx ]
    if not link_list:
      log.error(
        f'Invalid linkid {pfx} specified in {path}',category=log.IncorrectValue,module='routing')
      return {}
    result = link_list_prefix(link_list)
    if not result:
      log.error(
        f'Link with linkid {pfx} (used in {path}) does not have an IPv4/IPv6 prefix',category=log.MissingValue,module='routing')
    return result

  if pfx_type == 'role':
    link_list = [ lnk for lnk in topology.links if lnk.get('role',None) == pfx ]
    if not link_list:
      log.error(
        f'No link in the lab topology has role {pfx} specified in {path}',category=log.IncorrectValue,module='routing')
      return {}
    if len(link_list) > 5:
      log.warning(
        text=f'Link role {pfx} used in {path} was expanded into {len(link_list)} elements',
        module='routing')
    result = link_list_prefix(link_list)
    if not result:
      log.error(
        f'Link(s) with role {pfx} (used in {path}) do not have IPv4/IPv6 prefixes',category=log.MissingValue,module='routing')
    return result

  return {}
