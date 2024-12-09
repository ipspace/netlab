from box import Box
from netsim import data
from netsim.utils import log,strings
from netsim.augment import links

def clone_link(link_data: Box, nodename: str, clones: list[str]) -> list[Box]:
  cloned_links = []
  if nodename in [ i.node for i in link_data.get('interfaces',[]) ]:
    for c,clone in enumerate(clones):
      l = data.get_box(link_data)
      l.interfaces = []
      for intf in link_data.interfaces:
        intf_clone = data.get_box(intf)
        if intf.node == nodename:
          intf_clone.node = clone
        elif 'ifindex' in intf:
          intf_clone.ifindex = intf.ifindex + c
        l.interfaces.append(intf_clone)
      cloned_links.append(l)
  return cloned_links

"""
process_links - iterate over the 'links' attribute for the given item and clone any instances that involve node <nodename>
                <item> can be the global topology or a VLAN or VRF object with 'links'
"""
def process_links(item: Box, linkprefix: str, nodename: str, clones: list, topology: Box) -> None:
  for cnt,l in enumerate(list(item.links)):
    link_data = links.adjust_link_object(                                   # Create link data from link definition
                 l=l,
                 linkname=f'{linkprefix}.links[{cnt+1}]',
                 nodes=topology.nodes)
    if link_data is None:
      continue
    elif 'lag' in link_data:
      log.error(f"LAG links not yet supported by node.clone plugin, not cloning any members containing {nodename}",
                category=Warning, module='node.clone')
      continue

    cloned_links = clone_link(link_data,nodename,clones)
    if cloned_links:
      item.links.remove(l)
      item.links += cloned_links

"""
update_links - updates 'links' lists in VLAN and VRF objects
"""
def update_links(topo_items: str, nodename: str, clones: list, topology: Box) -> None:
  for vname,vdata in topology[topo_items].items():                           # Iterate over global VLANs or VRFs
    if isinstance(vdata,Box) and 'links' in vdata:
      process_links(vdata,f'{topo_items}.{vname}',nodename,clones,topology)

"""
clone_node - Clones a given node N times, creating additional links and/or interfaces for the new nodes
"""
def clone_node(node: Box, topology: Box) -> None:
  _p = { 'start': 1, 'step': 1 } + node.pop('clone',{})                      # Define cloning parameters
  if 'count' not in _p:
    log.error("Node {node.name} missing required attribute clone.count",     # Not validated by Netlab yet
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
    clone.interfaces = []                                                   # Start clean, remove reference to original node
    if 'id' in node:
      clone.id = node.id + c - 1                                            # Update any explicit node ID sequentially
    topology.nodes[ clone.name ] = clone
    clones.append( clone.name )

  if 'links' in topology:
    process_links(topology,'links',node.name,clones,topology)

  if 'groups' in topology:
    for groupname,gdata in topology.groups.items():
      if groupname[0]=='_':                                                 # Skip flags and other special items
        continue
      if node.name in gdata.get('members',[]):
        gdata.members.remove( node.name )
        gdata.members.extend( clones )

  if 'vlans' in topology:
    update_links('vlans',node.name,clones,topology)

  if 'vrfs' in topology:
    update_links('vrfs',node.name,clones,topology)

  topology.nodes.pop(node.name,None)                                        # Finally

"""
topology_expand - Main plugin function, expands the topology with cloned nodes and interfaces
"""
def topology_expand(topology: Box) -> None:
  for node in list(topology.nodes.values()):
    if 'clone' in node:
      clone_node( node, topology )
