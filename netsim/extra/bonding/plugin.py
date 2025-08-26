import typing

from box import Box

from netsim import api, data
from netsim.augment import devices
from netsim.utils import log, strings

_config_name = 'bonding'

ATTS_TO_MOVE = ['ipv4','ipv6','vlan','_vlan_mode','vlan_name','gateway']

'''
add_bond_interfaces - append interface data to node.interfaces for bonding template to read and implement
'''
def add_bond_interfaces(node: Box, bonds: typing.Dict[int,Box], topology: Box) -> None:
  bond_interface_name = topology.defaults.bonding.bond_interface_name
  for c,(ifindex,bond) in enumerate(bonds.items()):
    ifname = strings.eval_format(bond_interface_name, { 'ifindex': ifindex })

    #
    # TODO: Could make sure the layout is exactly like the 'lag' module needs it, to reuse provisioning logic
    # That means converting 'bonding.ifindex' to 'lag._parentindex' too!
    #
    bond_if = {
      'type': 'bond',
      'ifname': ifname,
      'name': f'bond {ifindex}',
      'bonding': { 'ifindex': ifindex, 'members': bond['members'], 'mode': bond.mode },
      'neighbors': bond['neighbors'],
      'ifindex': 50000 + c,
      'virtual_interface': True
    }
    if 'primary' in bond:
      bond_if['bonding']['primary'] = bond['primary']
    for af in ATTS_TO_MOVE:
      if af in bond:
        bond_if[af] = bond[af]     # Take the first one, if any
    node.interfaces.append(bond_if)

"""
Update the link and all neighbors with the new interface name
"""
def update_neighbors( node: Box, intf: Box, topology: Box ) -> bool:
  link = topology.links[ intf.linkindex-1 ]
  if 'virtual_interface' in intf or link.node_count!=2:
    log.error( f"{intf.name}: 'bonding.ifindex' can only be applied to interfaces on direct p2p links",
               category=log.IncorrectAttr,module=_config_name)
    return False

  intf.neighbors = [ { 'node': n.node, 'ifname': n.ifname } for n in intf.neighbors ]  # Clear any IP addresses from neighbors
  bond_interface_name = topology.defaults.bonding.bond_interface_name
  ifname = strings.eval_format(bond_interface_name, intf)
  for if2 in link.interfaces:
    if if2.node==node.name:
      if2.ifname = ifname
    else:
      nb = topology.nodes[if2.node]
      for if3 in nb.interfaces:
        for n2 in if3.neighbors:
          if n2.node==node.name:
            n2.ifname = ifname
  return True

'''
post_link_transform hook

Apply plugin config to nodes with interfaces marked with 'bonding.ifindex', for devices that support this plugin.
Executes after IP addresses are assigned, but before vlan gateways are fixed
'''
def post_link_transform(topology: Box) -> None:
  global _config_name
  bond_mode = topology.get('bonding.mode','active-backup')
  bonds : Box = data.get_empty_box()                   # Map of bonds per node, indexed by bonding.ifindex
  for node in topology.nodes.values():
    features = devices.get_device_features(node,topology.defaults)
    for intf in node.get('interfaces',[]):
      bond_ifindex = intf.get('bonding.ifindex',None)
      if bond_ifindex is None:
        continue
      if not 'bonding' in features:
        log.error( f"Node {node.name}({node.device}) does not support 'bonding.ifindex' used on {intf.name}",
                   category=log.IncorrectAttr,module=_config_name)
        continue

      if not update_neighbors(node,intf,topology):
        continue

      clone = data.get_box(intf)
      if node.name in bonds and bond_ifindex in bonds[node.name]:
        bonds[node.name][bond_ifindex]['members'].append( clone.ifname )
        for att in ATTS_TO_MOVE:
          intf.pop(att,None)
      else:
        mode = intf.get('bonding.mode',bond_mode)
        bonds[node.name][bond_ifindex] = { 'neighbors': intf.neighbors, 'members': [ clone.ifname ], 'mode': mode }
        for att in ATTS_TO_MOVE:                       # Move any ips (from first member link)
          if att in intf:
            bonds[node.name][bond_ifindex][att] = intf.pop(att,None)
      if intf.get('bonding.primary',False):
        bonds[node.name][bond_ifindex]['primary'] = intf.ifname
      intf.prefix = False                              # L2 interface

  for node in topology.nodes.values():                 # For each node
    if node.name in bonds:                             # ...that has 1 or more bonds
      add_bond_interfaces(node,bonds[node.name],topology)
      api.node_config(node,_config_name)               # Remember that we have to do extra configuration

