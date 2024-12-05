from box import Box
from netsim import data
from netsim.utils import log,strings
from netsim.augment import links

def clone_interfaces(link_data: Box, nodename: str, clones: list[str]) -> list[Box]:
  """
  update_ifindex - update any custom ifindex on the given interface
  """
  def update_ifindex(intf:Box, c:int) -> Box:
    ifindex = intf.get('ifindex',None)
    if ifindex is not None:
      intf = data.get_box(intf)                                             # Need to make a fresh copy
      intf.ifindex = ifindex + c + 1
    return intf
  
  ifs = []
  if nodename in [ i.node for i in link_data.interfaces ]:
     link_data.pop('_linkname',None)
     for c,clone in enumerate(clones):
       l = data.get_box(link_data)
       l.interfaces = [ { 'node': clone } ] + [ update_ifindex(i,c) for i in link_data.interfaces if i.node!=nodename ]
       ifs.append(l)
  return ifs

def update_vlan_access_links(topology: Box, nodename: str, clones: list) -> None:
  for vname,vdata in topology.vlans.items():                                # Iterate over global VLANs
    if not isinstance(vdata,Box):                                           # VLAN not yet a dictionary?
      continue                                                              # ... no problem, skip it
    if not 'links' in vdata:                                                # No VLAN links?
      continue                                                              # ... no problem, move on

    for cnt,l in enumerate(vdata.links):                                    # So far so good, now iterate over the links
      link_data = links.adjust_link_object(                                 # Create link data from link definition
                    l=l,
                    linkname=f'vlans.{vname}.links[{cnt+1}]',
                    nodes=topology.nodes)
      if link_data is not None:
        ifs = clone_interfaces(link_data,nodename,clones)
        vdata.links += ifs

"""
repeat_node - Clones a given node N times, creating additional links and/or interfaces for the new nodes
"""
def repeat_node(node: Box, topology: Box) -> None:
  count = node.pop('repeat',None)
  clones = []
  for c in range(2,count+2):                                                # Existing node is '1'
    clone = data.get_box(node)
    clone.name = strings.eval_format(topology.defaults.repeater.node_name_pattern, node + { 'id': c } )
    clone.interfaces = []                                                   # Start clean, remove reference to original node
    if 'id' in node:
      clone.id = node.id + c                                                # Update any explicit node ID sequentially
    topology.nodes += { clone.name: clone }
    clones.append( clone.name )

  for link in list(topology.get('links',[])):
    link_data = links.adjust_link_object(link,f'repeater{c}',topology.nodes)
    if link_data is None:
      continue
    if 'lag' in link_data:
      log.error("LAG links not yet supported by repeater plugin, ignoring...",
                category=Warning, module='repeater')
      continue  
    ifs = clone_interfaces(link_data,node.name,clones)
    topology.links += ifs

  if 'groups' in topology:
    for group in topology.groups.values():
      if node.name in group.members:
        group.members.extend( clones )

  if 'vlans' in topology:
    update_vlan_access_links(topology,node.name,clones)

"""
topology_expand - Main plugin function, expands the topology with cloned nodes and interfaces
"""
def topology_expand(topology: Box) -> None:
  for node in list(topology.nodes.values()):
    if 'repeat' in node:
      repeat_node( node, topology )
