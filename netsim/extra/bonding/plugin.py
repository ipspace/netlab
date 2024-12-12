import typing
from box import Box
from netsim.utils import log
from netsim import api,data
from netsim.augment import devices

_config_name = 'bonding'

'''
add_bond_interfaces - append interface data to node.interfaces for bonding template to read and implement
'''
def add_bond_interfaces(node: Box, bonds: dict[int,list[Box]]) -> None:
  last_linkindex = node.interfaces[-1].linkindex
  for c,(ifindex,members) in enumerate(bonds.items()):
    bond_if = {
      'linkindex': last_linkindex + 1 + c,
      'type': 'bond',
      'ifname': f'bond{ifindex}',  # XXX hardcoded, could make this a device template attribute
      'name': f'bond {ifindex}',
      'bonding': { 'ifindex': ifindex, 'members': [ m.ifname for m in members ] },
      'ifindex': 50000 + c,
      'virtual_interface': True
    }
    c = c + 1
    vlans = [ m.vlan for m in members if 'vlan' in m ]
    if vlans:
      bond_if.vlan = vlans[0]   # Take the first VLAN, hopefully consistent
    else:
      for af in ['ipv4','ipv6']:
        ips = [ m[af] for m in members if af in m ]
        if ips:
          bond_if[af] = ips[0]  # Take the first one, if any
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
      bonds : dict[int,list[Box]] = {}
      for intf in node.get('interfaces',[]):
        bond_ifindex = intf.get('bonding.ifindex',None)
        if not bond_ifindex:
          continue

        if 'virtual_interface' in intf or len(intf.get('neighbors',[]))!=1:
          log.error( f"{intf.name}: 'bonding.ifindex' can only be applied to interfaces on physical p2p links",
                     category=log.IncorrectAttr,module=_config_name)
          continue

        clone = data.get_box(intf)
        if bond_ifindex in bonds:
          bonds[ bond_ifindex ].append( clone )
        else:
          bonds[ bond_ifindex ] = [ clone ]

        for att in ['ipv4','ipv6','vlan']:      # Remove any ips or vlan
          intf.pop(att,None)
        intf.prefix = False                     # L2 interface

      if bonds:
        add_bond_interfaces(node,bonds)
        api.node_config(node,_config_name)               # Remember that we have to do extra configuration
