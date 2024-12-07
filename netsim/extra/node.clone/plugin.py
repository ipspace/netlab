from box import Box
from netsim import data
from netsim.utils import log,strings
from netsim.augment import links

def clone_interfaces(link_data: Box, nodename: str, clones: list[str]) -> list[Box]:
  ifs = []
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
      ifs.append(l)
  return ifs

"""
update_links - updates 'links' lists in VLAN and VRF objects
"""
def update_links(topo_items: Box, nodename: str, clones: list, topology: Box) -> None:
  for vname,vdata in topo_items.items():                                    # Iterate over global VLANs or VRFs
    if not isinstance(vdata,Box):                                           # VLAN not yet a dictionary?
      continue                                                              # ... no problem, skip it
    if not 'links' in vdata:                                                # No VLAN links?
      continue                                                              # ... no problem, move on

    for cnt,l in enumerate(list(vdata.links)):                              # So far so good, now iterate over the links
      link_data = links.adjust_link_object(                                 # Create link data from link definition
                    l=l,
                    linkname=f'vlans.{vname}.links[{cnt+1}]',
                    nodes=topology.nodes)
      if link_data is not None:
        ifs = clone_interfaces(link_data,nodename,clones)
        if ifs:
          vdata.links.remove(l)
          vdata.links += ifs

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

  orig_name = node.name
  node.name = strings.eval_format(name_format, node + { 'id': _p.start } )  # Rename first node as clone_01
  topology.nodes += { node.name: node }

  clones = [ node.name ]
  for c in range(_p.start+_p.step,_p.start+_p.count*_p.step,_p.step):       # Existing node is '1'
    clone = data.get_box(node)
    clone.name = strings.eval_format(name_format, node + { 'id': c, 'name': orig_name } )
    clone.interfaces = []                                                   # Start clean, remove reference to original node
    if 'id' in node:
      clone.id = node.id + c - 1                                            # Update any explicit node ID sequentially
    topology.nodes += { clone.name: clone }
    clones.append( clone.name )

  for link in list(topology.get('links',[])):                               # Make a copy of links list
    link_data = links.adjust_link_object(link,f'clone[{orig_name}]',topology.nodes)
    if link_data is None:
      continue
    if 'lag' in link_data:
      log.error("LAG links not yet supported by node.clone plugin",
                category=AttributeError, module='node.clone')
      continue  
    ifs = clone_interfaces(link_data,orig_name,clones)
    if ifs:
      topology.links.remove(link)                                           # Remove the original link
      topology.links += ifs

  if 'groups' in topology:
    for groupname,gdata in topology.groups.items():
      if groupname[0]=='_':                                                 # Skip flags and other special items
        continue
      if orig_name in gdata.get('members',[]):
        gdata.members.remove( orig_name )
        gdata.members.extend( clones )

  if 'vlans' in topology:
    update_links(topology.vlans,orig_name,clones,topology)

  if 'vrfs' in topology:
    update_links(topology.vrfs,orig_name,clones,topology)

  topology.nodes.pop(orig_name,None)                                        # Finally

"""
topology_expand - Main plugin function, expands the topology with cloned nodes and interfaces
"""
def topology_expand(topology: Box) -> None:
  for node in list(topology.nodes.values()):
    if 'clone' in node:
      clone_node( node, topology )
