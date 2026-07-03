from box import Box

from netsim.utils import log

_requires    = [ 'bgp' ]

'''
post_transform hook

We're going to iterate through IBGP neighbors on each node and remove cross-domain IBGP sessions.
At the same time, we're going to keep track of route reflectors for each AS/domain, and whenever
we find one, will validate that each domain-specific copy of an AS has a usable route reflector.
'''

def post_transform(topology: Box) -> None:
  rr_as: dict = {}                                          # Autonomous systems using route reflectors
  rr_domain_as: dict = {}                                   # Domain-specific AS RR flag

  for n, ndata in topology.nodes.items():
    if 'bgp' not in ndata.module:                           # Skip nodes not running BGP
      continue

    n_domain = ndata.get('bgp.domain','default')            # Get node domain, unspecified is 'default'
    n_as = str(ndata.get('bgp.as'))                         # Also get node AS number in string format, we'll need it a few times
    n_domain_as = f'{n_domain}:{n_as}'                      # We'll also need domain/AS pair for dictionary access

    if ndata.get('bgp.rr',False):                           # If the node is a route reflector...
      rr_as[n_as] = True                                    # ... mark AS as having route reflectors
      rr_domain_as[n_domain_as] = True                      # ... and remember that current AS has a RR in current domain

    ngb_list = []                                           # Rebuild BGP neighbor list
    for ngb in ndata.bgp.neighbors:                         # Iterate over neighbors
      if ngb.type != 'ibgp':                                # ... and keep all non-IBGP neighbors
        ngb_list.append(ngb)
        continue

      # Do we have a cross-domain IBGP session?
      #
      if topology.nodes[ngb.name].get('bgp.domain','default') != n_domain:
        if ngb.get('rr',False):                             # Is the cross-domain neighbor a route reflector?
          if n_domain_as not in rr_domain_as:
            rr_domain_as[n_domain_as] = False               # Mark this instance of current AS as potentially problematic
      else:
        ngb_list.append(ngb)                                # Intra-domain IBGP session, keep it

    ndata.bgp.neighbors = ngb_list                          # Replace the BGP neighbor list with the pruned list

  for domain_as,rr_state in rr_domain_as.items():           # Now iterate over domain/AS/RR flags
    if rr_state:                                            # If a domain instance of an AS has a route reflector...
      continue                                              # ... we're good to go

    # Houston, we have a problem. We have a domain instance of an AS that
    # has route reflectors, but unfortunately all reflectors happpen to be
    # in a different domain.
    (b_domain,b_as) = domain_as.split(':')
    log.error(
      f'BGP AS {b_as} is using route reflectors, but has no RRs in domain {b_domain}.\n' + \
      f'... You will have no IBGP route propagation within AS {b_as} in domain {b_domain}\n' + \
      f'... Make sure at least one router in AS {b_as} in domain {b_domain} is a route reflector',
      log.IncorrectValue,'bgp.domain')
