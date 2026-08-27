"""
Utility functions for the routing module
"""

from box import Box

from ...data import append_to_list, get_a_list, get_empty_box
from ...utils import log


def _link_list_prefix(link_list: list) -> Box:
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

def _extract_af(obj: Box) -> dict:
  result: dict = {}
  for af in log.AF_LIST:
    if af in obj:
      result[af] = get_a_list(obj[af])

  return result

def _eps_prefix(pfx: str, path: str, topology: Box) -> dict:
  pfx_data = topology.get(f'prefix.{pfx}',None)
  if pfx_data is None:
    log.error(
      f'Invalid named prefix {pfx} specified in {path}',category=log.IncorrectValue,module='routing')
    return {}
  if not pfx_data:
    log.error(
      f'Named prefix {pfx} used in {path} has no IPv4/IPv6 information',category=log.MissingValue,module='routing')
    return {}
  return _extract_af(pfx_data)

def _eps_vlan(pfx: str, path: str, topology: Box) -> dict:
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
    return _extract_af(pfx_data.prefix)

def _eps_link(pfx: str, path: str, topology: Box) -> dict:
  link_list = [ lnk for lnk in topology.links if lnk.get('linkid',None) == pfx ]
  if not link_list:
    log.error(
      f'Invalid linkid {pfx} specified in {path}',category=log.IncorrectValue,module='routing')
    return {}
  result = _link_list_prefix(link_list)
  if not result:
    log.error(
      f'Link with linkid {pfx} (used in {path}) does not have an IPv4/IPv6 prefix',category=log.MissingValue,module='routing')
  return result

def _eps_role(pfx: str, path: str, topology: Box) -> dict:
  link_list = [ lnk for lnk in topology.links if lnk.get('role',None) == pfx ]
  if not link_list:
    log.error(
      f'No link in the lab topology has role {pfx} specified in {path}',category=log.IncorrectValue,module='routing')
    return {}
  if len(link_list) > 5:
    log.warning(
      text=f'Link role {pfx} used in {path} was expanded into {len(link_list)} elements',
      module='routing')
  result = _link_list_prefix(link_list)
  if not result:
    log.error(
      f'Link(s) with role {pfx} (used in {path}) do not have IPv4/IPv6 prefixes',category=log.MissingValue,module='routing')
  return result

def _eps_pool(pfx: str, path: str, topology: Box) -> dict:
  pfx_data = topology.get(f'addressing.{pfx}',None)
  if pfx_data is None:
    log.error(
      f'Invalid address pool {pfx} specified in {path}',category=log.IncorrectValue,module='routing')
    return {}
  if not pfx_data:
    log.error(
      f'Address pool {pfx} used in {path} has no prefix information',category=log.MissingValue,module='routing')
    return {}
  else:
    return _extract_af(pfx_data)

PREFIXSET_LOOKUP: dict = {
  'prefix': _eps_prefix,
  'vlan': _eps_vlan,
  'link': _eps_link,
  'role': _eps_role,
  'pool': _eps_pool,
}

def eval_prefixset(pfx: str, path: str, topology: Box) -> dict:
  """
  Evaluate a generic routing prefix into a dictionary of ipv4/ipv6 prefix lists
  """

  if ':' in pfx:
    result = {'ipv6': [ pfx ]}
  elif pfx.count('.') > 1:
    result = {'ipv4': [ pfx ]}
  else:
    if '.' in pfx:
      (pfx_type,pfx) = pfx.split('.',1)
    else:
      pfx_type = 'prefix'

    if pfx_type not in PREFIXSET_LOOKUP:
      log.error(f'Invalid prefix namespace {pfx_type} in {path}',category=log.FatalError,module='routing')
      return {}

    result = PREFIXSET_LOOKUP[pfx_type](pfx,path,topology)

  if log.debug_active('prefixset'):
    print(f'prefixset: {pfx} -> {result}')

  return result
