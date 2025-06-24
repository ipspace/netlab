import typing
from box import Box
from netsim import api
from netsim.utils import log
from netsim.augment import devices

_config_name = 'bgp.confederation'
_requires    = [ 'bgp' ]

def post_transform(topology: Box) -> None:
  global _config_name
  confed = topology.get('bgp.confederation')
  if not confed:
    return
  
  for n, ndata in topology.nodes.items():
    if 'bgp' not in ndata.module:                           # Skip nodes not running BGP
      continue

    bgp_as = ndata.get('bgp.as')
    for casn,cdata in confed.items():                       # Iterate over all confederations
      members = cdata.get('members',[])
      if bgp_as in members:                                 # If this node is a member...

        features = devices.get_device_features(ndata,topology.defaults)
        if not features.get('bgp.confederation'):           # Check plugin support
          log.error( f"Node {ndata.name}({ndata.device}) does not support the bgp.confederation plugin",
                     category=log.IncorrectAttr,module=_config_name)
          continue

        ndata.bgp.confederation['as'] = casn
        ndata.bgp.confederation.peers = [ m for m in members if m!=bgp_as ]
        api.node_config(ndata,_config_name)                 # Remember that we have to do extra configuration

        for nb in ndata.get('bgp.neighbors',[]):            # Update remote AS used by ebgp peers
          neighbor = topology.nodes[ nb.name ]
          if neighbor.get('bgp.as') in members:             # Skip members of the same confederation
            continue
          for nb2 in neighbor.get('bgp.neighbors',[]):
            if nb2.name == n and nb2.type=='ebgp':
              nb2['as'] = casn                              # Update peer to use the confederation AS instead

        # TODO: Apply ibgp type community exchange, confed is really a new type of ebgp peer

        break
