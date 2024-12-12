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
  last_linkindex = node.interfaces[-1].linkindex
  for c,(ifindex,bond) in enumerate(bonds.items()):
    bond_if = {
      'linkindex': last_linkindex + 1 + c,
      'type': 'bond',
      'ifname': f'bond{ifindex}',  # XXX hardcoded, could make this a device template attribute
      'name': f'bond {ifindex}',
      'bonding': { 'ifindex': ifindex, 'members': [ m.ifname for m in bond['members'] ] },
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
  for node in topology.nodes.values():
    features = devices.get_device_features(node,topology.defaults)
    if 'bonding' in features:
      bonds : dict[int,Box] = {}
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
        if bond_ifindex in bonds:
          bonds[bond_ifindex]['members'].append( clone )
        else:
          bonds[bond_ifindex] = { 'interfaces': intf.interfaces, 'members': [ clone ] }
          for att in ['ipv4','ipv6']:    # Move any ips
            if att in intf:
              bonds[bond_ifindex][att] = intf.pop(att,None)

        intf.neighbors = [ { 'ifname': i.ifname, 'node': i.node } for i in link.interfaces if i.node!=node.name ]
        intf.type = 'p2p'
        intf.prefix = False              # L2 p2p interface

      if bonds:
        add_bond_interfaces(node,bonds)
        api.node_config(node,_config_name)               # Remember that we have to do extra configuration
