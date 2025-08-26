import typing

from box import Box

from netsim import data
from netsim.augment import links
from netsim.utils import log, strings

"""
clone_link - makes a copy of the given link for each clone, updating its node
"""
def clone_link(link_data: Box, nodename: str, clones: typing.List[str]) -> typing.List[Box]:
  cloned_links = []
  if nodename in [ i.node for i in link_data.get('interfaces',[]) ]:
    for c,clone in enumerate(clones):
      l = data.get_box(link_data)
      l.interfaces = []
      for intf in link_data.interfaces:
        intf_clone = data.get_box(intf)
        if intf.node == nodename:
          intf_clone.node = clone
        elif 'ifindex' in intf:                 # Update port on the peer side, if any
          intf_clone.ifindex = intf.ifindex + c
        l.interfaces.append(intf_clone)
      cloned_links.append(l)
  return cloned_links

"""
clone_lag - special routine to handle cloning of lag links
"""
def clone_lag(
      cnt: int,
      link_data: Box,
      nodename: str,
      clones: typing.List[str],
      topology: Box) -> typing.List[Box]:

  lag_members = link_data.get('lag.members')
  cloned_members = process_links(lag_members,f"lag[{cnt+1}].m",nodename,clones,topology)
  if not cloned_members:                                                      # If no lag members involve <nodename>
    return []                                                                 # .. exit

  cloned_lag_links = []
  for c,clone in enumerate(clones):
    l = data.get_box(link_data)                                               # Clone the lag link
    if l.get('lag.ifindex',0):
      l.lag.ifindex = l.lag.ifindex + c                                       # Update its ifindex, if any
    l.lag.members = []
    for clonelist in cloned_members:
      for intf in clonelist[c].interfaces:                                    # Update ifindex on interfaces
        if 'ifindex' in intf:
          intf.ifindex += c                                                   # May generate overlapping values
      l.lag.members.append( clonelist[c] )
    cloned_lag_links.append(l)
  return cloned_lag_links

"""
process_links - iterate over the 'links' attribute for the given item and clone any instances that involve node <nodename>
                <item> can be the global topology or a VLAN or VRF object with 'links'

                Returns a list of a list of cloned links
"""
def process_links(
      linkitems: list,
      linkprefix: str,
      nodename: str, clones: list,
      topology: Box) -> typing.List[typing.List[Box]]:

  result: typing.List[typing.List[Box]] = []
  for cnt,l in enumerate(list(linkitems)):
    link_data = links.adjust_link_object(                                    # Create link data from link definition
                 l=l,
                 linkname=f'{linkprefix}links[{cnt+1}]',
                 nodes=topology.nodes)
    if link_data is None:
      continue
    elif link_data.get('lag.members',None):
      cloned_links = clone_lag(cnt,link_data,nodename,clones,topology)
    else:
      cloned_links = clone_link(link_data,nodename,clones)

    if cloned_links:
      linkitems.remove(l)
      linkitems += cloned_links
      result.append(cloned_links)
  return result

"""
update_links - updates 'links' lists in VLAN and VRF objects
"""
def update_links(topo_items: str, nodename: str, clones: list, topology: Box) -> None:
  for vname,vdata in topology[topo_items].items():                           # Iterate over global VLANs or VRFs
    if isinstance(vdata,Box) and 'links' in vdata:
      process_links(vdata.links,f'{topo_items}.{vname}.',nodename,clones,topology)

"""
clone_node - Clones a given node N times, creating additional links and/or interfaces for the new nodes
"""
def clone_node(node: Box, topology: Box) -> None:
  _p = { 'start': 1, 'step': 1 } + node.pop('clone',{})                      # Define cloning parameters
  if 'count' not in _p:
    log.error("Node {node.name} missing required attribute clone.count",     # Not validated by Netlab
              category=AttributeError, module='node.clone')
    return
  for attr in _p:
    if not data.is_true_int(_p[attr]) or _p[attr]<=0:
      log.error(f"Attribute {attr} for node.clone must be a positive int",
                category=AttributeError, module='node.clone')
      return

  if 'include' in node:                                                      # Check for components
    log.error("Cannot clone component {node.name}, only elementary nodes",
              category=AttributeError, module='node.clone')
    return

  name_format = topology.defaults.clone.node_name_pattern
  clones = []
  for c in range(_p.start,_p.start+_p.count*_p.step,_p.step):
    clone = data.get_box(node)
    clone.name = strings.eval_format(name_format, node + { 'id': c } )

    clone.interfaces = []                                                    # Start clean, remove reference to original node
    if 'id' in node:
      clone.id = node.id + c - 1                                             # Update any explicit node ID sequentially
    if clone.name in topology.nodes:                                         # Check for existing nodes that may override
      clone = clone + topology.nodes[ clone.name ]                           # ...and merge its settings
    topology.nodes[ clone.name ] = clone
    clones.append( clone.name )

  if 'links' in topology:
    process_links(topology.links,"",node.name,clones,topology)

  if 'groups' in topology:
    for groupname,gdata in topology.groups.items():
      if groupname[0]=='_':                                                  # Skip flags and other special items
        continue
      if node.name in gdata.get('members',[]):
        gdata.members.remove( node.name )
        gdata.members.extend( clones )

  if 'vlans' in topology:
    update_links('vlans',node.name,clones,topology)

  if 'vrfs' in topology:
    update_links('vrfs',node.name,clones,topology)

  topology.nodes.pop(node.name,None)                                         # Finally

"""
topology_expand - Main plugin function, expands the topology with cloned nodes and interfaces
"""
def topology_expand(topology: Box) -> None:
  for node in list(topology.nodes.values()):
    if 'clone' in node:
      clone_node( node, topology )
