BGP_PREFIX_NAMES: dict = {
  'peer': 'BGP router ID',
  'nh'  : 'BGP next hop',
  'clusterid': 'RR cluster ID',
  'community': 'BGP community',
  'as_elements': 'AS numbers',
  'aspath': 'AS path',
  'locpref': 'BGP local preference',
  'med': 'BGP MED',
  'best': 'best path' }

BGP_COMMUNITY_KW = ['community', 'largeCommunity', 'extendedCommunity']

def check_community_kw(kw: str) -> None:
  global BGP_COMMUNITY_KW

  if kw not in BGP_COMMUNITY_KW:
    raise Exception(f'Invalid BGP community keyword {kw} (allowed: {",".join(BGP_COMMUNITY_KW)})')