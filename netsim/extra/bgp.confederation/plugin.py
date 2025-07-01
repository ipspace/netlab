import typing
from box import Box
from netsim import api
from netsim.utils import log
from netsim.augment import devices

_config_name = 'bgp.confederation'
_requires    = [ 'bgp' ]

CONFED_EBGP = 'confed_ebgp'

def init(topology: Box) -> None:
  topology.defaults.attributes.bgp_session_type.valid_values[ CONFED_EBGP ] = None
  topology.defaults.bgp.attributes._inherit_community[ CONFED_EBGP ] = 'ibgp'

  for af in log.AF_LIST:
    if CONFED_EBGP in topology.get(f'bgp.sessions.{af}',{}):
      log.error( f"Cannot use {CONFED_EBGP} in bgp.sessions", category=Warning,
                 more_hints=["Settings are inherited from the 'ibgp' key"] )
    if CONFED_EBGP in topology.get(f'bgp.activate.{af}',{}):
      log.error( f"Cannot use {CONFED_EBGP} in bgp.activate", category=Warning,
                 more_hints=["Settings are inherited from the 'ibgp' key"] )

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
          if nb.type != 'ebgp':                             # Only applies to EBGP peers
            continue
          neighbor = topology.nodes[ nb.name ]
          if neighbor.get('bgp.as') in members:             # Skip members of the same confederation
            continue
          nb.type = CONFED_EBGP
          for nb2 in neighbor.get('bgp.neighbors',[]):
            if nb2.name == n and nb2.type=='ebgp':
              nb2['as'] = casn                              # Update peer to use the confederation AS instead
              # nb2.type = CONFED_EBGP                      # DO NOT update BGP session type - peer device may not support this plugin

        break
