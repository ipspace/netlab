from box import Box
from netsim.utils import log
from netsim import api
from netsim.augment import devices
from netsim.augment import links

'''
check_device_support -- check whether the device used in a multihop EBGP session supports it
'''
def check_device_support(attr: str, ndata: Box, neigh: Box, topology: Box) -> None:
  features = devices.get_device_features(ndata,topology.defaults)
  if features.bgp.get('multihop',None):
    return
  
  log.error(
    f'EBGP multihop is not supported by node {ndata.name} (device {ndata.device})',
    log.IncorrectValue,'ebgp.utils')

def pre_link_transform(topology: Box) -> None:
  if not 'multihop' in topology.get('bgp',{}):
    return

  sessions = links.adjust_link_list(topology.bgp.multihop,topology.nodes,'bgp.multihop[{link_cnt}]')
  topology.bgp.multihop = sessions
  for s in sessions:
    s.type = 'tunnel'
    s.linkindex = links.get_next_linkindex(topology)
    s._bgp_session = True
    for intf in s.interfaces:
      node = topology.nodes[intf.node]
      if not 'loopback' in node:
        log.error(
          'Cannot establish EBGP multihop session from node {intf.name}: node has no loopback interface',
          'ebgp.multihop',log.IncorrectValue)
        continue
      for af in ['ipv4','ipv6']:
        if af in node.loopback:
          intf[af] = node.loopback[af]
      intf.bgp.multihop = 255
      intf._bgp_session = True

  topology.links.extend(sessions)

def post_transform(topology: Box) -> None:
  config_name = api.get_config_name(globals())        # Get the plugin configuration name
  for ndata in topology.nodes.values():
    intf_count = len(ndata.interfaces)
    ndata.interfaces = [ intf for intf in ndata.interfaces if not intf.get('_bgp_session',None) ]

    if len(ndata.interfaces) != intf_count:           # Did the interface count change?
      api.node_config(ndata,config_name)              # We must have some multihop sessions, add extra config

  topology.links = [ link for link in topology.links if not link.get('_bgp_session',None) ]
