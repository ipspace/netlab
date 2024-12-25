import typing
from box import Box
from netsim.utils import log, strings
from netsim import api,data
from netsim.augment import devices

_config_name = 'bonding'

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
    for af in ['ipv4','ipv6']:
      if af in bond:
        bond_if[af] = bond[af]     # Take the first one, if any
    node.interfaces.append(bond_if)

'''
post_transform hook

Apply plugin config to nodes with interfaces marked with 'bonding.ifindex', for devices that support this plugin
'''
def post_transform(topology: Box) -> None:
  global _config_name
  bond_mode = topology.get('bonding.mode','active-backup')
  bonds : Box = data.get_empty_box()                   # Map of bonds per node, indexed by bonding.ifindex
  for node in topology.nodes.values():
    features = devices.get_device_features(node,topology.defaults)
    for intf in node.get('interfaces',[]):
      bond_ifindex = intf.get('bonding.ifindex',None)
      if not bond_ifindex:
        continue
      if not 'bonding' in features:
        log.error( f"Node {node.name}({node.device}) does not support 'bonding.ifindex' used on {intf.name}",
                   category=log.IncorrectAttr,module=_config_name)
        continue

      link = topology.links[ intf.linkindex-1 ]
      if 'virtual_interface' in intf or link.node_count!=2:
        log.error( f"{intf.name}: 'bonding.ifindex' can only be applied to interfaces on direct p2p links",
                   category=log.IncorrectAttr,module=_config_name)
        continue
      clone = data.get_box(intf)
      if node.name in bonds and bond_ifindex in bonds[node.name]:
        bonds[node.name][bond_ifindex]['members'].append( clone.ifname )
        for att in ['ipv4','ipv6']:
          intf.pop(att,None)
      else:
        mode = intf.get('bonding.mode',bond_mode)
        bonds[node.name][bond_ifindex] = { 'neighbors': intf.neighbors, 'members': [ clone.ifname ], 'mode': mode }
        for att in ['ipv4','ipv6']:                    # Move any ips (from first member link)
          if att in intf:
            bonds[node.name][bond_ifindex][att] = intf.pop(att,None)
      if intf.get('bonding.primary',False):
        bonds[node.name][bond_ifindex]['primary'] = intf.ifname
      
      #
      # Clean up interface neighbors leaving only directly reachable peers (as opposed to - say - 
      # VLAN neighbors in the form of other hosts), moving the rest to bond[x].neighbors
      #
      intf.neighbors = [ { 'ifname': i.ifname, 'node': i.node } for i in link.interfaces if i.node!=node.name ]
      intf.prefix = False                              # L2 interface
      intf.pop('name',None)

  # Interface neighbors may need to be updated to reflect the new bonded interface
  bond_interface_name = topology.defaults.bonding.bond_interface_name
  for node in topology.nodes.values():                 # For each node
    if node.name in bonds:                             # ...that has 1 or more bonds
      for bond in bonds[node.name].values():           # ...for each bond
        for i in bond.neighbors:                       # ...for each neighbor of that bond
          if i.node in bonds:                          # ...check if the node also has bonds
            for i2,b2 in bonds[i.node].items():        # If so, for each such bond
              if i.ifname in b2['members']:            # if the interface connecting to <node> is a member
                i.ifname = strings.eval_format(bond_interface_name, { 'ifindex': i2 })
                continue
      add_bond_interfaces(node,bonds[node.name],topology)
      api.node_config(node,_config_name)               # Remember that we have to do extra configuration
