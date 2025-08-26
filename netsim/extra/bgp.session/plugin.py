import typing

from box import Box

from netsim import api, modules
from netsim.utils import log
from netsim.utils import routing as _bgp

_config_name = 'bgp.session'
_requires    = [ 'bgp' ]

def pre_link_transform(topology: Box) -> None:
  global _config_name
  # Error if BGP module is not loaded
  if 'bgp' not in topology.module:
    log.error(
      'BGP Module is not loaded.',
      log.IncorrectValue,
      _config_name)

'''
Get a list of attributes to apply to IBGP or EBGP sessions
'''
def get_attribute_list(apply_list: typing.Any, topology: Box) -> list:
  if apply_list is None or apply_list is True or (isinstance(apply_list,list) and '*' in apply_list):
    return topology.defaults.bgp.attributes.session.attr

  return list(apply_list)

'''
Mark that the node needs a plugin config, and potentially cleared BGP sessions
'''
def mark_plugin_config(node: Box, ngb: Box) -> None:
  global _config_name

  api.node_config(node,_config_name)                  # Remember that we have to do extra configuration
  _bgp.clear_bgp_session(node,ngb)

'''
Apply attributes supported by bgp.session plugin to a single neighbor
Returns False is some of the attributes are not supported
'''
def apply_neighbor_attributes(node: Box, ngb: Box, intf: typing.Optional[Box], apply_list: list, topology: Box) -> bool:
  global _config_name

  OK = True
  for attr in apply_list:
    attr_value = modules.get_effective_module_attribute(path=f'bgp.{attr}',intf=intf,node=node)
    if not attr_value:                                  # Attribute not defined in interface or node, move on
      continue

    # Check that the node(device) supports the desired attribute
    OK = OK and _bgp.check_device_attribute_support(attr,node,ngb,topology,_config_name)
    ngb[attr] = attr_value                              # Set neighbor attribute from interface/node value
    mark_plugin_config(node,ngb)                        # Remember that we have to do extra configuration

  return OK

'''
Copy local session attributes to BGP neighbors because we need
them there in the configuration templates
'''
def copy_local_attributes(ndata: Box, topology: Box) -> None:
  apply = ndata.get('bgp.session.apply',{ 'ebgp': None })     # By default we apply all session attributes only to EBGP neighbors

  OK = True
  if 'ibgp' in apply:                                         # Do we apply session attributes to IBGP neighbors?
    apply_list = get_attribute_list(apply.ibgp,topology)      # Get attributes to apply to IBGP neighbors
    for ngb in  _bgp.neighbors(ndata,select=['ibgp']):        # Iterate over all neighbors using node attributes
      OK = OK and apply_neighbor_attributes(ndata,ngb,None,apply_list,topology)

  if not OK:                                                  # Skip the second step if we encountered unsupported device
    return                                                    # ... doesn't make sense to throw the same error(s) twice

  if 'ebgp' in apply:                                         # Do we apply session attributes to EBGP neighbors?
    apply_list = get_attribute_list(apply.ebgp,topology)      # Get attributes to apply to IBGP neighbors

    # Iterate over neighbors that have associated interfaces (all EBGP neighbors are supposed to be directly connected)
    for (intf,ngb) in _bgp.intf_neighbors(ndata,select=['ebgp']):
      apply_neighbor_attributes(ndata,ngb,intf,apply_list,topology)

'''
For platforms that collect tcp_ao secrets in global management profiles
we have to build a list of secrets so we can refer to them in neighbor
configurations
'''
def process_tcpao_password(neigh: Box, ndata: Box) -> None:
  global _config_name

  if not 'password' in neigh:
    log.error(
      f'BGP neighbor {neigh.name} on node {ndata.name} has TCP-AO configured without a password',
      log.MissingValue,
      _config_name)
    return
  
  pwd = neigh.password
  if not '_ao_secrets' in ndata.bgp:
    ndata.bgp._ao_secrets = []

  if not pwd in ndata.bgp._ao_secrets:
    ndata.bgp._ao_secrets.append(pwd)

def process_tcpao_secrets(ndata: Box,topology: Box) -> None:
  for ngb in _bgp.neighbors(ndata):
    if 'tcp_ao' in ngb:
      process_tcpao_password(ngb,ndata)

'''
Check whether a node runs BFD with any BGP neighbors
'''
def process_bfd_requests(ndata: Box, topology: Box) -> None:
  for ngb in _bgp.neighbors(ndata):
    if not 'bfd' in ngb:                                    # No BFD, no worries
      continue
    if not ngb.bfd:                                         # BFD set to False (or some similar stunt)
      ngb.pop('bfd')
      continue

    if not 'bfd' in ndata.module:                           # Do we have BFD enabled on this node?
      log.error(
        f'node {ndata.name} is running BFD with BGP neighbor {ngb.name} but does not use BFD module',
        log.IncorrectValue,
        _config_name)

'''
Zap a BGP neighbor: remove all usable IP addresses, local_if and ifindex
'''
def zap_bgp_neighbor(ngb: Box) -> None:
  for rm in ('ipv4','ipv6','local_if','ifindex'):
    ngb.pop(rm,None)
  
  ngb._zapped = True

'''
Get link index from an interface index to check whether the BGP neighbor
is attached to the same link
'''
def get_intf_linkindex(ndata: Box, ifindex: int) -> int:
  t_intf = [ intf for intf in ndata.interfaces if intf.ifindex == ifindex ]
  return t_intf[0].linkindex if t_intf else 0

'''
Given a neighbor (ngb) of a route server (ndata), set the rs_client flag on the
neighbor's EBGP session with the route server.

If the neighbor is another route server, remove IPv4 and IPv6 addresses from the
EBGP session to ensure we don't have RS-to-RS sessions

The only way to get this done is to do a reverse lookup, trying to find us in
the neighbor's neighbor list. Note that this will find any EBGP session with the
route server. Let's just say that parallel EBGP sessions with route servers
should be discouraged ;)
'''
def set_rs_client(ndata: Box, ngb: Box, topology: Box) -> None:
  global _config_name

  r_ndata = topology.nodes.get(ngb.name,{})               # Get neighbor's node data
  for r_ngb in _bgp.neighbors(r_ndata):                   # Iterate over neighbor's neighbors
    if r_ngb.name != ndata.name:                          # Nope, not us
      continue
    if r_ngb.get('rs',False):                             # RS-to-RS session?
      zap_bgp_neighbor(r_ngb)                             # Nope, not doing that
      zap_bgp_neighbor(ngb)
    else:
      r_ngb.rs_client = True                              # Else mark remote node as being a RS client
      mark_plugin_config(r_ndata,r_ngb)                   # Remember that we have to do extra configuration
      r_ndata.bgp.rs_client = True                        # And also that the node is a RS client
      if not _bgp.check_device_attribute_support('rs_client',r_ndata,r_ngb,topology,_config_name):
        log.error(
          f'Node {r_ndata.name} cannot have an EBGP session with a BGP Route Server {ndata.name}',
          category=log.IncorrectType,
          module='bgp.session')

'''
Deal with RS requests:

* Remove EBGP sessions between route servers
* Set (and check) rs_client flag on RS neighbors
'''
def process_rs_requests(ndata: Box,topology: Box) -> bool:
  global _config_name
  have_rs = False

  # First pass: set rs_client flag on Route Server clients
  for ngb in _bgp.neighbors(ndata):                         # Iterate over all neighbors
    if not ngb.get('rs',False):                             # Neighbor is not a RS client, get out
      continue
    if ngb.type == 'ibgp':                                  # Cannot have an IBGP RS session
      ngb.pop('rs')
      continue
    set_rs_client(ndata,ngb,topology)
    have_rs = True

  return have_rs

'''
Remove full mesh of EBGP sessions on links with route servers

In the first pass, we identify all links with route servers collecting
rs_linkindex values from BGP neighbors if the BGP neighbor has rs_client
flag set.

In the second pass, we zap all BGP neighbors that are not route servers
or RS clients on links we identified in the first pass.
'''

def cleanup_rs_mesh(topology: Box) -> None:
  for ndata in topology.nodes.values():
    for ngb in _bgp.neighbors(ndata,select=['ebgp']):         # Iterate over all neighbors
      if 'rs_client' in ngb:                                  # Found a RS client
        for x_ngb in _bgp.neighbors(ndata,select=['ebgp']):   # Now iterate over all other neighbors
          if x_ngb.ifindex != ngb.ifindex:                    # Skip neighbors over different interfaces
            continue
          if 'rs' in x_ngb or 'rs_client' in x_ngb:           # Skip RS-related sessions
            continue
          zap_bgp_neighbor(x_ngb)

'''
Cleanup BGP neighbors

* Remove all zapped neighbors from the neighbor list
* 
'''
def cleanup_bgp_neighbors(topology: Box) -> None:
  for ndata in topology.nodes.values():
    if 'bgp' not in ndata or 'neighbors' not in ndata.bgp:
      continue

    ndata.bgp.neighbors = [ ngb for ngb in ndata.bgp.neighbors if '_zapped' not in ngb ]
    for vdata in ndata.get('vrfs',{}).values():
      if 'bgp' in vdata and 'neighbors' in vdata.bgp:
        vdata.bgp.neighbors = [ ngb for ngb in vdata.bgp.neighbors if '_zapped' not in ngb ]

'''
post_transform hook

As we're applying interface attributes to BGP sessions, we have to copy
interface BGP parameters supported by this plugin into BGP neighbor parameters
'''

def post_transform(topology: Box) -> None:
  have_rs = False
  for ndata in topology.nodes.values():
    if not 'bgp' in ndata.get('module',[]):                 # Skip nodes not running BGP
      continue

    _bgp.cleanup_neighbor_attributes(ndata,topology,topology.defaults.bgp.attributes.session.attr)
    copy_local_attributes(ndata,topology)
    process_tcpao_secrets(ndata,topology)
    process_bfd_requests(ndata,topology)
    have_rs = process_rs_requests(ndata,topology) or have_rs

  # We need to do the RS-related EBGP session cleanup in a second pass
  #
  if have_rs:
    cleanup_rs_mesh(topology)
    cleanup_bgp_neighbors(topology)
