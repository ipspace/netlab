
from box import Box

from netsim.utils import log

from ... import tunnel as _tunnel
from .. import _p2p

_config_name = 'tunnel.gre'

def pre_transform(topology: Box) -> None:
  '''
  pre_transform hook: set tunnel link type, check whether GRE tunnels are P2P
  '''
  _tunnel.set_tunnel_type(topology)
  for link in _tunnel.links(topology,'gre'):
    if len(link.interfaces) != 2:
      log.error(
        f'A GRE tunnel must have exactly two nodes attached to it (link {link._linkname})',
        category=log.IncorrectAttr,
        module='tunnel.gre')

def post_transform(topology: Box) -> None:
  '''
  post_transform hook: check device support, set tunnel interface source/destination
  '''

  # Use shared P2P tunnel function to check feature support
  #
  node_iflist = _p2p.feature_check(topology,t_mode='gre',t_desc='GRE tunnels',t_af=True,t_default_af='ipv4')
  _p2p.tunnel_source(topology,node_iflist,default_af='ipv4',t_name='GRE')

  if log.get_error_count():                                 # Has someone reported an error?
    return                                                  # Might have been us, no reason to continue

  _p2p.tunnel_destination(topology,node_iflist,t_mode='gre',mtu_adjust={'ipv4': 24,'ipv6': 48})
