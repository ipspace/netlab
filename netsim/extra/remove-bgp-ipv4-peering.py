#
# Plugin that removes all ipv4 bgp peering, leaving only neighbors with ipv6
#
# Usage:
# plugins: [ remove-bgp-ipv4-peering ]
#

from box import Box

def post_transform(topo: Box) -> None:
  """
  Processes BGP neighbors to remove ipv4 peering
  """

  def remove_ipv4(n):
      n.pop('ipv4')
      return n

  for node in topo.nodes.values():
   if 'bgp' in node:
     node.bgp.neighbors = [ remove_ipv4(n) for n in node.bgp.neighbors if 'ipv6' in n and n.ipv6 != False ]
