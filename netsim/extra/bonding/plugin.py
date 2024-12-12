import typing
from box import Box
from netsim.utils import log
from netsim import api,data
from netsim.augment import devices

_config_name = 'bonding'

'''
add_bond_interfaces - append interface data to node.interfaces for bonding template to read and implement
'''
def add_bond_interfaces(node: Box, bonds: dict[int,Box]) -> None:
  for c,(ifindex,bond) in enumerate(bonds.items()):
    ifname = f'bond{ifindex}'  # XXX hardcoded, could make this a device template attribute
    bond_if = {
      'type': 'lag',  # TODO "bond"?
      'ifname': ifname,
      'name': f'bond {ifindex}',
      'bonding': { 'ifindex': ifindex, 'members': bond['members'], 'mode': bond.mode },
      'interfaces': bond['interfaces'],
      'ifindex': 50000 + c,
      'virtual_interface': True
    }
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
    if 'bonding' in features:
      for intf in node.get('interfaces',[]):
        bond_ifindex = intf.get('bonding.ifindex',None)
        if not bond_ifindex:
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
          bonds[node.name][bond_ifindex] = { 'interfaces': intf.neighbors, 'members': [ clone.ifname ], 'mode': mode }
          for att in ['ipv4','ipv6']:                  # Move any ips (from first member link)
            if att in intf:
              bonds[node.name][bond_ifindex][att] = intf.pop(att,None)

        intf.neighbors = [ { 'ifname': i.ifname, 'node': i.node } for i in link.interfaces if i.node!=node.name ]
        intf.type = 'p2p'
        intf.prefix = False                            # L2 p2p interface
        intf.pop('name',None)

  for node in topology.nodes.values():
    if node.name in bonds:
      for bond in bonds[node.name].values():
        for i in bond.interfaces:
          if i.node in bonds:
            for i2,b2 in bonds[i.node].items():
              if i.ifname in b2['members']:
                i.ifname = f'bond{i2}'                 # Correct neighbor name
                continue
      add_bond_interfaces(node,bonds[node.name])
      api.node_config(node,_config_name)               # Remember that we have to do extra configuration
