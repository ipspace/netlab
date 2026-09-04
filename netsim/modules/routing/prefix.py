#
# Generic routing module: 
#
# * Routing policies (route maps)
# * Routing filters (prefixes, communities, as-paths)
# * Static routes
#
import ipaddress
import typing

from box import Box

from ...augment import devices as a_devices
from ...data import append_to_list, get_empty_box
from ...utils import log
from . import utils as _utils


def expand_prefix_entry(p_entry: Box, path: str, topology: Box) -> Box:
  """
  Expand a single prefix-list entry:

  * Transform 'pool' and 'prefix' keywords into 'ipv4' and 'ipv6'
  * Adjust min/max values to be AF-specific
  """

  def add_af_info(data: Box) -> None:
    for af in log.AF_LIST:
      if af in data:
        append_to_list(p_entry,af,data[af])

  for pool in p_entry.get('pool',[]):
    add_af_info(topology.addressing[pool])

  for prefix in p_entry.get('prefix',[]):
    pfx_data = _utils.eval_prefixset(prefix,path,topology)
    for af in log.AF_LIST:
      if af in pfx_data:
        p_entry[af] = p_entry.get(af,[]) + pfx_data[af]

  for kw in ('pool','prefix'):
    p_entry.pop(kw,None)

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

def adjust_pfx_min_max(
      p_entry: Box,
      m_kw: str,
      af: str,
      p_name: str,
      node: Box,
      original_seq: int,
      min_pfx_len: int,
      max_pfx_len: int) -> None:
  """
  adjust_pfx_min_max: Adjust prefix list entry min/max keywords

  Arguments:
  - p_entry: the prefix we're checking
  - m_kw: the parameter we're checking (min/max)
  - af: the address family we're checking
  - p_name: prefix list name for error messages
  - node: node data (needed for error messages)
  - min_pfx_len: minimum prefix length we can match (depends on prefix)
  - max_pfx_len: maximum prefix length we can match (depends on address family)
  """
  if m_kw not in p_entry:
    return

  if af not in p_entry[m_kw]:                     # At this point, the values are already dicts due to
    p_entry.pop(m_kw,None)                        # ... expand_prefix_entry
    return                                        # ... so we can just pop the unnecessary entry

  m_value = p_entry[m_kw].get(af,None)
  if m_value < min_pfx_len:                       # The minimum prefix length is too low
    if min_pfx_len > max_pfx_len:                 # Is this caused by /32 (or /128) prefix on an IOS-like device?
      log.error(
        f'Cannot use prefix filter {m_kw} keyword with prefix {p_entry[af]}',
        more_data=[f'Node {node.name} (device {node.device}) policy {p_name} sequence# {original_seq}'],
        category=log.IncorrectValue,
        module='routing')
    else:
      log.error(
        f'Prefix filter {af}.{m_kw} value should be >= {min_pfx_len} (limited by {p_entry[af]})',
        more_data=[f'Node {node.name} (device {node.device}) policy {p_name} sequence# {original_seq}'],
        category=log.IncorrectValue,
        module='routing')

  if m_value > max_pfx_len:
    log.error(
      f'Prefix filter {af}.{m_kw} value should be <= {max_pfx_len} (limited by address family)',
      more_data=[f'Node {node.name} (device {node.device}) policy {p_name} sequence# {original_seq}'],
      category=log.IncorrectValue,
      module='routing')

  p_entry[m_kw] = m_value                         # Replace the min/max dict with per-AF value

def create_pfx_af_entry(
      p_entry: Box,                     # Original prefix entry (to get the min/max values)
      af: str,
      af_item: str,                     # Single prefix item (generated from AF lists)
      seq: int,                         # Prefix list element sequence number
      original_seq: int,                # Original sequence number (used in error message)
      p_name: str,
      node: Box,
      min_strict: bool = False) -> Box:
  """
  create_af_entry: create AF-specific prefix-list entry

  Arguments:
  - p_entry: Original prefix list entry
  - af: Address family we're focusing on
  - af_item: An element of the prefix entry to generate a new (non-list) prefix entry
  - p_name: Prefix list name (for error messages)
  - node: Node data (needed for error messages)
  - min_strict: Is device enforcing strict min/max rules (min/max have to be greater than prefix length)?
  """
  af_p_entry = get_empty_box()                              # Create a new p_entry
  af_p_entry[af] = af_item                                  # ... with a single AF item
  af_p_entry.sequence = seq                                 # ... insert sequence number
  af_p_entry.action = p_entry.get('action','permit')        # ... and permit/deny action

  pfx_max = 32 if af == 'ipv4' else 128                     # Find longest
  pfx_len = ipaddress.ip_network(af_item).prefixlen         # ... and shortest sensible prefix length

  for m_kw in ('min','max'):                                # ... and use them to validate min/max entries
    if m_kw not in p_entry:                                 # min/max KW not specified?
      continue
    af_p_entry[m_kw] = p_entry[m_kw]                        # ... otherwise copy it into new prefix entry
    pfx_min = pfx_len + 1 if min_strict else pfx_len
    adjust_pfx_min_max(                                     # Check the values ...
      af_p_entry,m_kw,af,                                   # ... using new entry, keyword and AF
      p_name,node,original_seq,                             # ... data needed for error message
      min_pfx_len=pfx_min,max_pfx_len=pfx_max)              # ... and limits on min/max values

  if 'min' in af_p_entry and 'max' in af_p_entry and af_p_entry.min > af_p_entry.max:
    log.error(
      f'Prefix filter {af}.min should be <= {af}.max',
      more_data=[
        f'Node {node.name} (device {node.device}) policy {p_name}'
        f' sequence# {original_seq} prefix {af_item}'],
      category=log.IncorrectValue,
      module='routing')

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
    x_path = f'nodes.{node.name}.routing.{o_name}.{p_name} sequence#{p_entry.sequence}'
    x_entry = expand_prefix_entry(node.routing[o_name][p_name][p_idx],x_path,topology)
    node.routing[o_name][p_name][p_idx] = x_entry

  node.routing[o_name][p_name] = sorted(node.routing[o_name][p_name],key=lambda O: O.get('sequence',10))
  features = a_devices.get_device_features(node,topology.defaults)
  min_strict = features.get('routing.prefix.strict',False)
  af_prefix: dict = {}                                      # Prepare dictionary of per-AF prefix lists
  for af in ('ipv4','ipv6'):                                # Iterate over address families (sorry, no CLNS or IPX)
    af_prefix[af] = []                                      # Start with an emtpy per-AF list
    seq = 100                                               # ... with initial sequence# 100
    for p_entry in node.routing[o_name][p_name]:            # Iterate over prefix list entries
      if af in p_entry:                                     # Is the current AF in the prefix list entry?
        for af_item in p_entry[af]:                         # ... iterate over elements in the AF list        
          af_p_entry = create_pfx_af_entry(                 # Create a new (single-item) prefix entry
                          p_entry,af,af_item,               # ... from original entry and AF info
                          seq,p_entry.sequence,             # ... using a new sequence number
                          p_name,node,                      # ... and the pfx_name/node data
                          min_strict=min_strict)
          af_prefix[af].append(af_p_entry)                  # Append new prefix entry to per-AF list
          seq += 10                                         # ... and increase sequence number

    if af_prefix[af]:                                       # Do we have a non-empty per-AF prefix list?
      node.routing['_'+o_name][af][p_name] = af_prefix[af]  # ... yes, save it
    else:
      node.routing['_'+o_name][af][p_name] = create_empty_prefix_list(af)      

  return None                                               # No need to do additional checks
