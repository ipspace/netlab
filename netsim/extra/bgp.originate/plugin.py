from box import Box

from netsim.augment import links
from netsim.data import get_box

_requires    = [ 'bgp' ]

"""
Have to complete the fix of bgp.originate attribute (can't do everything through the settings)
"""
def init(topology: Box) -> None:
  o_dict = topology.defaults.bgp.attributes.node.originate
  for kw in ('use','named','type'):
    o_dict._subtype.pop(kw,None)

def post_node_transform(topology: Box) -> None:
  for n, ndata in topology.nodes.items():
    if 'bgp' not in ndata.get('module',[]):                 # Skip nodes not running BGP
      continue

    o_list = ndata.get('bgp.originate',[])                  # Skip nodes without the 'originate' list
    if not o_list:
      continue

    for o_idx,o_entry in enumerate(o_list):                 # Iterate over entries in originate list
      o_link = get_box({                                    # Create a loopback link for each originate entry
                 'interfaces': [ { 'node': n }],
                 'type'      : 'loopback',
                 'name'      : f'BGP originate #{o_idx + 1}',
                 '_linkname' : f'bgp.originate.{n}[{o_idx + 1}]',
                 'linkindex' : links.get_next_linkindex(topology)
               })

      for af in ['ipv4','ipv6']:                            # Populate the link with AF information
        if af in o_entry:
          o_link.prefix[af] = o_entry[af]                   # Link prefix is copied from the originate list
          o_link.interfaces[0][af] = 1                      # Loopback address is the first address in the prefix
          o_link.bgp.advertise = True                       # Configure BGP advertising (just in case)

      topology.links.append(o_link)                         # ... and append the new loopback link to the links list

    ndata.bgp.pop('originate')                              # Originate list is no longer needed
