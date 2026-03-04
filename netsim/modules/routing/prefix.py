#
# Generic routing module: 
#
# * Routing policies (route maps)
# * Routing filters (prefixes, communities, as-paths)
# * Static routes
#
import typing

from box import Box

from ...data import get_new_box
from ...utils import log

"""
expand_prefix_entry:

* Transform 'pool' and 'prefix' keywords into 'ipv4' and 'ipv6'
* Adjust min/max values to be AF-specific
"""
def expand_prefix_entry(p_entry: Box, topology: Box) -> Box:
  extra_data = None
  if 'pool' in p_entry:
    extra_data = topology.addressing[p_entry.pool]
    p_entry.pop('pool',None)

  if 'prefix' in p_entry:
    extra_data = topology.prefix[p_entry.prefix]
    p_entry.pop('prefix',None)

  if extra_data:                                  # Did we get any new information?
    for af in ('ipv4','ipv6'):                    # Replace potential IPv4/IPv6 values with it
      if af in extra_data:
        p_entry[af] = extra_data[af]

  for kw in ('min','max'):                        # Next, normalize the min/max values
    if kw not in p_entry:
      continue
    if isinstance(p_entry[kw],dict):              # Are they already dicts?
      continue                                    # Cool, move on

    # Create a dict with an identical entry for every AF active in the prefix list entry
    p_entry[kw] = { af: p_entry[kw] for af in log.AF_LIST if af in p_entry }
    if not p_entry[kw]:                           # Did we create an empty dict (no AFs?)
      p_entry.pop(kw,None)

  return p_entry

"""
adjust_pfx_min_max: Adjust prefix list entry min/max keywords
"""
def adjust_pfx_min_max(p_entry: Box, m_kw: str, af: str, p_name: str, node: Box) -> None:
  if m_kw not in p_entry:
    return

  if af not in p_entry[m_kw]:                     # At this point, the values are already dicts due to
    p_entry.pop(m_kw,None)                        # ... expand_prefix_entry
    return                                        # ... so we can just pop the unnecessary entry

  m_value = p_entry[m_kw].get(af,None)
  if m_value < 0:                                 
    log.error(
      f'Prefix filter {m_kw} value should be >= 0 (policy {p_name}#{p_entry.sequence} on node {node.name})',
      category=log.IncorrectValue,
      module='routing')
    return

  m_max = 32 if af == 'ipv4' else 128
  if m_value > m_max:
    log.error(
      f'Prefix filter {af}.{m_kw} value should be <= {m_max} (policy {p_name}#{p_entry.sequence} on node {node.name})',
      category=log.IncorrectValue,
      module='routing')
    return

  p_entry[m_kw] = m_value                         # Replace the min/max dict with per-AF value

"""
create_af_entry: create AF-specific prefix-list entry
"""
def create_pfx_af_entry(p_entry: Box, af: str, p_name: str, node: Box) -> Box:
  af_p_entry = get_new_box(p_entry)                         # Create a copy of the current p_entry
  for af_x in ('ipv4','ipv6'):                              # ... remove all other address families
    if af_x in p_entry and af_x != af:
      af_p_entry.pop(af_x,None)

  for m_kw in ('min','max'):
    adjust_pfx_min_max(af_p_entry,m_kw,af,p_name,node)

  return af_p_entry

"""
create_empty_prefix_list: Create an empty per-AF prefix list
"""
def create_empty_prefix_list(af: str) -> list:
  p_entry = { 'sequence': 10, 'action': 'deny' }
  p_entry[af] = '0.0.0.0/0' if af == 'ipv4' else '::/0'
  return [ p_entry ]

"""
expand_prefix_list:

* Transform all entries in the prefix list
* Build IPv4 and IPv6 prefix lists
"""
def expand_prefix_list(p_name: str,o_name: str,node: Box,topology: Box) -> typing.Optional[list]:
  for (p_idx,p_entry) in enumerate(node.routing[o_name][p_name]):
    node.routing[o_name][p_name][p_idx] = expand_prefix_entry(node.routing[o_name][p_name][p_idx],topology)

  node.routing[o_name][p_name] = sorted(node.routing[o_name][p_name],key=lambda O: O.get('sequence',10))
  af_prefix: dict = {}                                      # Prepare dictionary of per-AF prefix lists
  for af in ('ipv4','ipv6'):                                # Iterate over address families (sorry, no CLNS or IPX)
    af_prefix[af] = []                                      # Start with an emtpy per-AF list
    for p_entry in node.routing[o_name][p_name]:            # Iterate over prefix list entries
      if af in p_entry:                                     # Is the current AF in the prefix list entry?
        af_p_entry = create_pfx_af_entry(p_entry,af,p_name,node)
        af_prefix[af].append(af_p_entry)                    # create af-specific entry and append it to per-AF list

    if af_prefix[af]:                                       # Do we have a non-empty per-AF prefix list?
      node.routing['_'+o_name][af][p_name] = af_prefix[af]  # ... yes, save it
    else:
      node.routing['_'+o_name][af][p_name] = create_empty_prefix_list(af)      

  return None                                               # No need to do additional checks
