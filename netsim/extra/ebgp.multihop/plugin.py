from box import Box
from netsim.utils import log
from netsim import api,data
from netsim.augment import devices
from netsim.augment import links
from netsim.data.validate import validate_attributes

'''
check_device_support -- check whether the device used in a multihop EBGP session supports it
'''
def check_device_support(ndata: Box, topology: Box) -> None:
  features = devices.get_device_features(ndata,topology.defaults)
  if features.bgp.get('multihop',None):
    return
  
  log.error(
    f'EBGP multihop is not supported by node {ndata.name} (device {ndata.device})',
    log.IncorrectValue,'ebgp.multihop')

def pre_transform(topology: Box) -> None:
  config_name  = api.get_config_name(globals())        # Get the plugin configuration name
  session_idx  = data.find_in_list(['ebgp.utils','bgp.session'],topology.plugin)
  multihop_idx = data.find_in_list([ config_name ],topology.plugin)

  if session_idx is not None and session_idx > multihop_idx:
    log.error(
      'ebgp.multihop plugin must be included after bgp.session/ebgp.utils plugin',
      log.IncorrectValue,'ebgp.multihop')

def pre_link_transform(topology: Box) -> None:
  if not 'multihop' in topology.get('bgp',{}):
    return

  sessions = links.adjust_link_list(topology.bgp.multihop,topology.nodes,'bgp.multihop[{link_cnt}]')
  topology.bgp.multihop = sessions
  for s in sessions:
    for attr in list(s.keys()):                       # Change session attributes into BGP link attributes
      if attr in ['interfaces','_linkname']:          # Skip internal attributes
        continue
      s.bgp[attr] = s[attr]                           # Turn a session attribute into 'bgp.x' attribute
      s.pop(attr,None)
    
    s.type = 'tunnel'
    s.linkindex = links.get_next_linkindex(topology)
    s._bgp_session = True

    validate_attributes(
      data=s,                                         # Validate pseudo-link data
      topology=topology,
      data_path=s._linkname,
      data_name=f'EBGP session',
      attr_list=['link'],                             # We're checking link attributes
      modules=['bgp'],                                # ... against BGP parameters
      module_source='topology',
      module='ebgp.multihop')                         # Validation is called from 'ebgp.multihop' plugin

    for intf in s.interfaces:
      node = topology.nodes[intf.node]
      for attr in list(intf.keys()):                  # Change interface attributes into BGP attributes
        if attr in ['node']:                          # Skip internal attributes
          continue
        intf.bgp[attr] = intf[attr]                   # Turn an interface attribute into 'bgp.x' attribute
        intf.pop(attr,None)

      validate_attributes(
        data=intf,                                    # Validate interface data
        topology=topology,
        data_path=f'{s._linkname}.{intf.node}',
        data_name=f'BGP neighbor',
        attr_list=['interface','link'],               # We're checking interface or link attributes
        modules=['bgp'],                              # ... against BGP attributes
        module_source='topology',
        module='ebgp.multihop')                       # Function is called from 'ebgp.multihop' plugin

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
      check_device_support(ndata,topology)
      api.node_config(ndata,config_name)              # We must have some multihop sessions, add extra config

  topology.links = [ link for link in topology.links if not link.get('_bgp_session',None) ]
