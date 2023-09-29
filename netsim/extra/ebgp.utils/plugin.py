from box import Box
from netsim.utils import log
from netsim import api
from netsim.augment import devices

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
post_transform hook

As we're applying interface attributes to BGP sessions, we have to copy
interface BGP parameters supported by this plugin into BGP neighbor parameters
'''

def post_transform(topology: Box) -> None:
  config_name = api.get_config_name(globals())              # Get the plugin configuration name

  for n, ndata in topology.nodes.items():
    if not 'bgp' in ndata.module:                           # Skip nodes not running BGP
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
        attr_value = intf.get('bgp',{}).get(attr,None) or ndata.get('bgp', {}).get(attr,None)
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

    # Create EBGP multihop sessions if requested
    for key in ['bgp','bgp.vpn']:
      if 'multihop' in ndata.get(key, {}):
        if not ndata.get('bgp',{}).get('neighbors',[]):
          ndata.bgp.neighbors = []
        for neigh,multihop in ndata[key].multihop.items():
          if neigh not in topology.nodes:
            log.error( 
              f'multihop: Neighbor {neigh} not found for node {ndata.name} (device {ndata.device})',
              log.IncorrectValue,'ebgp.utils')
          nb = topology.nodes[neigh]
          if 'bgp' not in nb:
            log.error( 
              f'multihop: Neighbor {neigh} does not have BGP enabled for node {ndata.name} (device {ndata.device})',
              log.IncorrectValue,'ebgp.utils')
          feature = 'multihop' if key=='bgp' else 'vpn.multihop'
          check_device_attribute_support(feature,ndata,nb,topology)
          check_device_attribute_support(feature,nb,ndata,topology)
 
          if multihop is True:
            multihop = 64
          elif int(multihop) < 1 or int(multihop) > 255:
            log.error( 
              f'multihop: Value {multihop} is out of range [1..255] from node {ndata.name} (device {ndata.device}) to {neigh}',
              log.IncorrectValue,'ebgp.utils')
          def add_multihop_neighbor(n1,n2):
            neighbor_data = {
              'name': n2.name,
              'as': n2.bgp.get('as'),
              'type': "ebgp",
              'multihop': int(multihop)
            }
            af_count = 0
            for af in ["ipv4","ipv6"]:
              if af in n2.loopback:
                neighbor_data['vpnv4' if key=='bgp.vpn' else af] = str(netaddr.IPNetwork(n2.loopback[af]).ip)
                af_count = af_count + 1
            if af_count==0:
              log.error( 
                f'multihop: Neighbor {n2.name} does not have a suitable ipv4/v6 loopback IP for node {n1.name} (device {n1.device})',
                log.IncorrectValue,'ebgp.utils')
            n1.bgp.neighbors.append(neighbor_data)
            api.node_config(n1,config_name)
 
          # Add session on both sides
          add_multihop_neighbor(ndata,nb)
          add_multihop_neighbor(nb,ndata)
