from box import Box

from netsim import api

"""
Enable 'proxy_arp' attribute per VRF
"""
def init(topology: Box) -> None:
  topology.defaults.attributes.vrf.proxy_arp = None

"""
Add 'proxy_arp' flag and trigger custom config file for any interfaces that are
part of a VRF with proxy ARP enabled
"""
def post_transform(topology: Box) -> None:

  if not topology.get('vrfs',[]):
    return

  target_vrfs = [ v for v,d in topology.vrfs.items() if 'proxy_arp' in d ]

  config_name = api.get_config_name(globals())

  # Iterate over node[x].interfaces that are part of a VRF with proxy_arp enabled
  for n, ndata in topology.nodes.items():
    for i in ndata.interfaces:
      if i.type in ['lan','p2p','svi'] and 'vrf' in i and i.vrf in target_vrfs \
        and ('ipv4' in i or 'ipv6' in i):
          i.proxy_arp = True
          api.node_config(ndata,config_name)
