'''
Bridge-specific data transformation:

* Define 'br_default' VLAN 1 if it's not defined
* Set vlan.mode to 'bridge' on bridge devices
* Set vlan.access on bridge interfaces without the 'vlan' parameter
'''

from box import Box

from ..augment import links
from ..data import append_to_list, get_box, global_vars
from ..modules import _dataplane
from ..utils import log
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

    append_to_list(ndata,'module','vlan')                   # Activate VLAN module in bridge node and topology
    append_to_list(topology,'module','vlan')

  return br_found

"""
Go through the links and add 'vlan.access: br_default' to every interface of
a bridge node that does not have a VLAN parameter
"""
def add_default_access_vlan(topology: Box) -> None:
  BR_DEFAULT = global_vars.get_const('bridge.default_vlan.name','br_default')

  for link in topology.get('links',[]):
    if 'vlan' in link:                                      # A link already has VLAN parameters, skip it
      continue
    for intf in link.get('interfaces',[]):
      n_role = topology.nodes[intf.node].get('role','router')
      if n_role != 'bridge':                                # Not a bridge interface, skip it
        continue
      if len(link.interfaces) == 1:
        log.error(
          f'Connecting a bridge node {intf.node} to a stub link {link._linkname} makes no sense',
          category=log.IncorrectValue,
          module='bridge')
        continue
      if len(link.interfaces) > 2:
        log.error(
          f'Use the "bridge" attribute to specify that you want to use a bridge node {intf.node}' +\
          f' to implement a multi-access link {link._linkname}',
          category=log.IncorrectAttr,
          module='bridge')
        continue
      if 'vlan' in intf:                                    # The interface has VLAN parameters, skip it
        continue
      intf.vlan.access = BR_DEFAULT

"""
Get next internal VLAN for an isolated bridge domain
"""
def get_next_internal_vlan(start: int, use: str) -> int:
  while start < 4090:                                       # Skip some of the high-end VLANs
    if not _dataplane.is_id_used('vlan_id',start):          # Is the VLAN used anywhere?
      _dataplane.extend_id_set('vlan_id',set([start]))      # No, grab it
      return start                                          # ... and return it to the caller
    start = start + 1                                       # Otherwise, try the next one

  log.error(
    f'Cannot allocate an internal VLAN for {use} -- I ran out of VLANs',
    category=log.IncorrectValue,
    module='vlan')
  return 1                                                  # We need some value, and it doesn't matter

"""
A multi-access link with a "bridge" attribute specifying a bridge node is
expanded into multiple P2P links with the bridge node.
"""
def expand_multiaccess_links(topology: Box) -> None:
  skip_linkattr = list(topology.defaults.vlan.attributes.phy_ifattr)
  ok_phy_attr   = ['bandwidth', 'mtu', 'stp']
  del_linkattr  = ['linkindex', 'interfaces', 'bridge']
  int_vlan_id = global_vars.get_const('bridge.internal_vlan.start',100)

  for link in list(topology.get('links',[])):
    b_name = link.get('bridge',None)
    if not b_name:                                          # Is this one of the relevant links?
      continue                                              # No, move on

    if b_name not in topology.nodes:                        # Is the bridge name equal to a node name?
      continue                                              # No, it's a name of a Linux bridge

    if topology.nodes[b_name].get('role','') != 'bridge':
      log.error(
        f'Node {b_name} specified in "bridge" attribute on link {link._linkname} must have "role" set to "bridge"',
        category=log.IncorrectType,
        module='bridge')
      continue

    # Do we have any of the physical attributes on the link? For the moment, let's assume that's an error
    #
    wrong_attr = [ k for k in link.keys() if k in skip_linkattr and k not in del_linkattr + ok_phy_attr ]
    if wrong_attr:
      log.error(
        text=f'Link attribute(s) {",".join(wrong_attr)} cannot be used on {link._linkname}',
        more_hints=f"The link is implemented with a bridge node {b_name}",
        category=log.IncorrectAttr,
        module='bridge')
      continue

    link_data = { k:v for k,v in link.items() if k in ok_phy_attr }
    br_intf = get_box({'node': b_name })                    # Create the interface for the bridge node
    br_node = topology.nodes[b_name]                        # Get the node data
    int_vlan_id = get_next_internal_vlan(int_vlan_id,'multi-access link {link._linkname}')
    vname = f'br_vlan_{int_vlan_id}'                        # Create the internal VLAN

    br_node.vlans[vname] = { k:v for k,v in link.items() if k not in del_linkattr }
    br_node.vlans[vname].id = int_vlan_id                   # ... set its ID
    br_node.vlans[vname].mode = 'bridge'                    # ... and make it a L2-only VLAN
    br_intf.vlan.access = vname                             # ... and use it on the bridge interface

    for link_cnt,intf in enumerate(link.interfaces,1):
      l_data = get_box(link_data)                           # Copy the link data
      l_data._linkname = f'{link._linkname}.{link_cnt}'     # Create unique link and and linkindex
      l_data.linkindex = links.get_next_linkindex(topology)
      l_data.interfaces = [ get_box(br_intf), intf ]        # ... recreate P2P interfaces
      topology.links.append(l_data)                         # ... and append the new P2P link to the links

    topology.links.remove(link)                             # Finally, remove original link

def pre_transform(topology: Box) -> None:
  if create_default_VLAN(topology):                         # If we have any bridge nodes ...
    add_default_access_vlan(topology)                       # Add 'vlan.access' to non-VLAN bridge ports  

  expand_multiaccess_links(topology)                        # Unrelated, check the 'bridge' attribute on
                                                            # ... multi-access links and expand them
