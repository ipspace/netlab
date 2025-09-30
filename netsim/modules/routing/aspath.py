#
# Generic routing module -- AS path filters
#
import typing

from box import Box

from ...data import get_box
from .normalize import (
  normalize_routing_entry,
)

"""
normalize_aspath_entry: turn non-dictionary entries into dictionaries with 'path' attribute
"""
def normalize_aspath_entry(p_entry: typing.Any, p_idx: int) -> Box:
  if not isinstance(p_entry,Box):
    p_entry = get_box({ 'path': p_entry })

  if 'path' not in p_entry and 'list' not in p_entry and 'regexp' not in p_entry:
    p_entry.path = '.*'

  if 'path' in p_entry:
    if isinstance(p_entry.path,list):
      p_list = [ str(p) for p in p_entry.path ]
      p_entry.path = ' '.join(p_list)

  normalize_routing_entry(p_entry,p_idx)
  return p_entry

"""
Number AS path ACLs (some platforms refer to them by numbers)
"""

def number_aspath_acl(p_name: str,o_name: str,node: Box,topology: Box) -> None:
  numacl = node.routing._numobj[o_name]
  if p_name not in numacl:
    maxacl = max([ 0 ] + [ acl for acl in numacl.values() ])
    numacl[p_name] = maxacl + 1
