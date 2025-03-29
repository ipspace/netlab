'''
Bridge-specific data transformation:

* Define 'br_default' VLAN 1 if it's not defined
* Set vlan.mode to 'bridge' on bridge devices
* Set vlan.access on bridge interfaces without the 'vlan' parameter
'''
import typing

from box import Box, BoxList

from ..utils import log
from ..data import global_vars,append_to_list,get_box
from ..augment import links
from . import select_nodes_by_role

"""
Set the default VLAN mode on bridges to 'bridge' in the pre-transform hook
to prevent VLAN module from setting it to some other value.

Also, define 'br_default' node VLAN if it's not defined

Return 'True' if we found at least one bridge (so we need further processing)
"""
def create_default_VLAN(topology: Box) -> bool:
  BR_DEFAULT = global_vars.get_const('bridge.default_vlan.name','br_default')
  BR_DEF_ID  = global_vars.get_const('bridge.default_vlan.id',1)
  br_found = False

  for ndata in select_nodes_by_role(topology,'bridge'):
    br_found = True
    if not ndata.get('vlan.mode',None):                     # Do we have vlan.mode set on the node?
      ndata.vlan.mode = 'bridge'                            # ... nope, default is bridge
    if not isinstance(ndata.vlans,Box):                     # Check the 'vlans' data type just to be on the safe side
      continue
    if 'id' not in ndata.vlans[BR_DEFAULT]:                 # Create default VLAN box on the fly and check for id
      ndata.vlans[BR_DEFAULT].id = BR_DEF_ID

  return br_found

"""
Go through the links and add 'vlan.access: br_default' to every interface of
a bridge node that does not have a VLAN parameter

Return 'True' if we found at least one "default" link attached to a bridge
"""
def add_default_access_vlan(topology: Box) -> bool:
  BR_DEFAULT = global_vars.get_const('bridge.default_vlan.name','br_default')
  link_found = False

  for link in topology.get('links',[]):
    if 'vlan' in link:                                      # A link already has VLAN parameters, skip it
      continue
    for intf in link.get('interfaces',[]):
      if 'vlan' in intf:                                    # The interface has VLAN parameters, skip it
        continue
      n_role = topology.nodes[intf.node].get('role','router')
      if n_role != 'bridge':                                # Not a bridge interface, skip it
        continue
      intf.vlan.access = BR_DEFAULT
      link_found = True
      append_to_list(link,'_br_list',intf)                  # Remember the bridges we found

  return link_found

"""
When exactly one of the nodes on link with more than two nodes is a bridge,
expand the link into multiple P2P links with the bridge node. Print a warning
(and do nothing) if there are more than two bridges attached to the link
"""
def expand_multiaccess_links(topology: Box) -> None:
  for link in list(topology.get('links',[])):
    if '_br_list' not in link:                              # Is this one of the relevant links?
      continue                                              # No, move on

    br_list = link._br_list                                 # Get the list of bridges
    link.pop('_br_list',None)                               # ... and remove it from the link

    if not br_list:                                         # Empty list?
      continue                                              # Weird, but we've seen weirder things

    if len(br_list) > 1:                                    # Multiple bridges on multi-access links confuse us
      br_names = [ intf.node for intf in br_list ]
      log.warning(
        text=f'Multiple bridges ({",".join(br_names)}) attached to multi-access link {link._linkname}',
        more_hints='netlab can expand only multi-access links attached to a single bridge',
        module='bridge')
      continue

    br_intf = br_list[0]                                    # Remember the bridge interface
    link_cnt = 0
    for intf in link.interfaces:
      if intf != br_intf:                                   # Did we find an interesting interface?
        l_data = get_box(link)                              # Copy the link data
        link_cnt += 1
        l_data._linkname = f'{link._linkname}.{link_cnt}'   # Create unique link and and linkindex
        l_data.linkindex = links.get_next_linkindex(topology)
        l_data.interfaces = [ get_box(br_intf), intf ]      # ... recreate P2P interfaces
        topology.links.append(l_data)                       # ... and append the new P2P link to the links

    topology.links.remove(link)                             # Finally, remove original link

def pre_transform(topology: Box) -> None:
  if not create_default_VLAN(topology):                     # Add default bridge VLAN
    return                                                  # ... exit if we found no bridges

  if not add_default_access_vlan(topology):                 # Add 'vlan.access' to non-VLAN bridge ports
    return                                                  # ... exit if we found no relevant links
  
  expand_multiaccess_links(topology)                        # Expand multi-access links 