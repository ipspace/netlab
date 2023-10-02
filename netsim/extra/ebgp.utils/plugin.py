from box import Box
from netsim.utils import log
from netsim import api
from netsim.augment import devices
from netsim.augment.links import adjust_link_object
from netsim.data.validate import must_be_int

import netaddr

def pre_link_transform(topology: Box) -> None:
  # Error if BGP module is not loaded
  if 'bgp' not in topology.module:
    log.error(
      'BGP Module is not loaded.',
      log.IncorrectValue,
      'ebgp_utils')

'''
check_device_attribute_support -- using device BGP features, check whether the
device supports the attribute applied to a BGP neighbor
'''
def check_device_attribute_support(attr: str, ndata: Box, neigh: Box, topology: Box) -> None:
  features = devices.get_device_features(ndata,topology.defaults)
  if features.get('bgp',{}).get(attr,None):
    return
  
  log.error(
    f'Attribute {attr} used on BGP neighbor {neigh.name} is not supported by node {ndata.name} (device {ndata.device})',
    log.IncorrectValue,'ebgp.utils')

'''
Based on globally defined bgp.multihop, create virtual multihop interfaces for the bgp 
module to create sessions from

This needs to run after loopback interfaces have been created, with IP addresses 
(in augment/nodes.transform)
'''
def post_node_transform(topology: Box) -> None:
  config_name = api.get_config_name(globals())     # Get the plugin configuration name

  def loopback_ips(n:Box):
    return { k:str(netaddr.IPNetwork(n.loopback[k]).ip) 
             for k in ['ipv4','ipv6'] if k in n.get('loopback',{}) }

  def add_interface(n1:Box, n2:Box, session:Box) -> None:
    ifindex = len(n1.interfaces) + 1
    n1.interfaces.append( {
      'type': 'multihop',
      'ifindex': ifindex,
      'ifname': f"multihop-{n1.name}-{n2.name}",
      'virtual_interface': True,
      'neighbors': [ { 'node': n2.name, 'ifindex': ifindex, **loopback_ips(n2) } ],
      **loopback_ips(n1),
      # Attributes validated by code below, not specifically against list of session attributes
      'bgp': { k:v for k,v in session.items() if k not in ['interfaces','_linkname'] }
    })
    api.node_config(n1,config_name)

  for i,s in enumerate(topology.get('bgp.multihop',{})):
    name = f'bgp-multihop[{i}]'
    session = adjust_link_object(s,name,topology.nodes)
    if not must_be_int(session,key='ttl',path=name,min_value=1,max_value=255):
      continue
    session.ttl = session.get('ttl',64)

    n1 = topology.nodes[session.interfaces[0].node]
    n2 = topology.nodes[session.interfaces[1].node]

    add_interface(n1,n2,session)
    add_interface(n2,n1,session)

'''
post_transform hook

As we're applying interface attributes to BGP sessions, we have to copy
interface BGP parameters supported by this plugin into BGP neighbor parameters
'''
def post_transform(topology: Box) -> None:
  config_name = api.get_config_name(globals())              # Get the plugin configuration name

  for n, ndata in topology.nodes.items():
    if 'bgp' not in ndata.module:                           # Skip nodes not running BGP
      continue

    # Cleanup ebgp.utils attributes with local significance from neighbors
    for attr in topology.defaults.bgp.attributes.ebgp_utils.local:
      for neigh in ndata.get('bgp', {}).get('neighbors', []):
        neigh.pop(attr,None)

      for vname,vdata in ndata.get('vrfs',{}).items():
        if not vdata.get('bgp.neighbors',None):
          continue
        for neigh in vdata.bgp.neighbors:
          neigh.pop(attr,None)

    # Iterate over all ebgp.utils link/interface attributes
    for intf in ndata.interfaces:
#      print(f'node: {ndata.name} intf {intf.ifname} / {intf.ifindex}')
      for attr in topology.defaults.bgp.attributes.ebgp_utils.attr:
        attr_value = (intf.get('bgp',{}).get(attr,None) 
                      or ndata.get('bgp', {}).get(attr,None) 
                      or topology.get('bgp', {}).get(attr,None))
        if not attr_value:                                  # Attribute not defined in node or interface, move on
          continue
        
#        print(f'.. attr {attr} value {attr_value}')
        # Iterate over all BGP neighbors trying to find neighbors on this interface
        for neigh in ndata.get('bgp', {}).get('neighbors', []):
#          print(f'.... neighbor: {neigh.name} {neigh.ifindex} {neigh.type}')
          if neigh.type == 'ebgp' and neigh.ifindex == intf.ifindex:
            check_device_attribute_support(attr,ndata,neigh,topology)
            neigh[attr] = attr_value                        # Found the neighbor, set neighbor attribute
            api.node_config(ndata,config_name)              # And remember that we have to do extra configuration
#            print(f'...... setting value {neigh}')

        if 'vrf' not in intf:                               # Not a VRF interface?
           continue                                         # ... great, move on

        # Now do the same 'copy interface attribute to neighbors' thing for VRF neighbors
        for neigh in ndata.vrfs[intf.vrf].get('bgp', {}).get('neighbors', []):
          if neigh.ifindex == intf.ifindex and neigh.type == 'ebgp':
            neigh[attr] = attr_value                        # Found the neighbor, set neighbor attribute
            api.node_config(ndata,config_name)              # And remember that we have to do extra configuration

    # Cleanup any multihop sessions
    ndata.pop('bgp.multihop',None)