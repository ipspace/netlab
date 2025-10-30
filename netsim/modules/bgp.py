#
# BGP transformation module
#
import typing

from box import Box

from .. import data
from ..augment import devices, groups
from ..data import global_vars
from ..data.types import must_be_asn, must_be_list
from ..data.validate import validate_item
from ..utils import log
from ..utils import routing as _rp_utils
from . import _Module, _routing

BGP_DEFAULT_SESSIONS: typing.Dict[str,list] = {
}

BGP_VALID_SESSION_TYPE: list = []

BGP_DEFAULT_COMMUNITY_KW: typing.Final[dict] = {
  'standard': 'standard',
  'extended': 'extended'
}

BGP_INHERIT_COMMUNITY: Box

def setup_bgp_constants(topology: Box) -> None:
  global BGP_DEFAULT_SESSIONS, BGP_VALID_SESSION_TYPE, BGP_INHERIT_COMMUNITY

  bgp_session_values = topology.defaults.attributes.bgp_session_type.valid_values
  # Add confed_ebgp to valid values if the topology is using confederations
  if 'bgp.confederation' in topology:
    bgp_session_values.confed_ebgp = None

  # Valid session types are reconstructed from the valid values of the bgp.sessions.ipv4 global attribute
  # We're assuming there's no difference between IPv4 and IPv6
  BGP_VALID_SESSION_TYPE = list(bgp_session_values)

  # We're assuming all address families are active on all session types
  for af in log.AF_LIST:
    BGP_DEFAULT_SESSIONS[af] = BGP_VALID_SESSION_TYPE

  # Finally, copy the pointer to BGP community inheritance and limit it to valid session types
  BGP_INHERIT_COMMUNITY = topology.defaults.bgp.attributes._inherit_community
  for cst in list(BGP_INHERIT_COMMUNITY):
    if cst not in BGP_VALID_SESSION_TYPE:
      BGP_INHERIT_COMMUNITY.pop(cst)

def check_bgp_parameters(node: Box, topology: Box) -> None:
  if not "bgp" in node:  # pragma: no cover (should have been tested and reported by the caller)
    return
  if not "as" in node.bgp:
    log.error(
      f"Node {node.name} has BGP enabled but no AS number specified",
      log.MissingValue,
      'bgp')
    return

  must_be_asn(parent=node,key='bgp.as',path=f'nodes.{node.name}',module='bgp')

  if "community" in node.bgp:
    bgp_comm = node.bgp.community
    if isinstance(bgp_comm,str):
      node.bgp.community = { 'ibgp' : [ bgp_comm ], 'ebgp': [ bgp_comm ]}
    elif isinstance(bgp_comm,list):
      node.bgp.community = { 'ibgp' : bgp_comm, 'ebgp': bgp_comm }
    elif not(isinstance(bgp_comm,dict)):
      log.error(
        f"bgp.community attribute in node {node.name} should be a string, a list, or a dictionary (found: {bgp_comm})",
        log.IncorrectType,
        'bgp')
      return

    for k in node.bgp.community.keys():
      if not k in ['ibgp','ebgp']:
        log.error(
          text=f"Invalid BGP community setting in {k} node {node.name}",
          category=log.IncorrectValue,
          module='bgp')
      else:
        must_be_list(
          parent=node.bgp.community,
          path=f'nodes.{node.name}.bgp.community',
          key=k,
          valid_values=topology['defaults.attributes.global.bgp_community_type.valid_values'],
          module='bgp')

def validate_bgp_sessions(node: Box, sessions: Box, attribute: str) -> bool:
  OK = True
  for k in list(sessions.keys()):
    if not k in log.AF_LIST:
      log.error(
        f'Invalid address family in bgp.{attribute} in node {node.name}',
        log.IncorrectValue,
        'bgp')
      OK = False
    else:
      if must_be_list(
          parent=sessions,
          key=k,
          path=f'nodes.{node.name}.bgp.{attribute}',
          true_value=BGP_VALID_SESSION_TYPE,
          valid_values=BGP_VALID_SESSION_TYPE,
          module='bgp') is None:
        OK = False        

  return OK

"""
find_bgp_rr: find route reflectors in the specified autonomous system

Given an autonomous system and lab topology, return a list of node names that are route reflectors in that AS
"""
def find_bgp_rr(bgp_as: int, topology: Box) -> typing.List[Box]:
  return [ n 
    for n in topology.nodes.values() 
      if 'bgp' in n and n.bgp["as"] == bgp_as and n.bgp.get("rr",None) ]

"""
bgp_neighbor: Create BGP neighbor data structure

* n - neighbor node data
* intf - neighbor interface data (could be addressing prefix or whatever is in the interface neighbor list)
* ctype - session type (ibgp or ebgp or localas_ibgp)
* extra_data - anything else we might want to pass to the neighbor data structure
"""
def bgp_neighbor(n: Box, intf: Box, ctype: str, sessions: Box, extra_data: typing.Optional[dict] = None) -> typing.Optional[Box]:
  ngb = data.get_box(extra_data or {})
  ngb.name = n.name
  ngb["as"] = n.bgp.get("as")
  ngb["type"] = ctype
  af_count = 0
  for af in ["ipv4","ipv6"]:
    if ctype in sessions.get(af,[]):
      if af in intf:
        af_count = af_count + 1
        if isinstance(intf[af],bool):
          ngb[af] = intf[af]
        else:
          ngb[af] = _rp_utils.get_intf_address(intf[af])

  return ngb if af_count > 0 else None

"""
get_neighbor_rr: create extra data for bgp_neighbor function

Returns { rr: him } dict if the neighbor happens to be a RR. That dict will be merged with
the rest of the neighbor data
"""
def get_neighbor_rr(n: Box) -> typing.Optional[typing.Dict]:
  if "rr" in n.get("bgp"):
    return { "rr" : n.bgp.rr }

  return {}

"""
get_remote_ibgp_endpoint: find the remote endpoint of an IBGP session

* Loopback interface if it exists
* Remote CP endpoint if the remote device is a daemon without a loopback interface
* Otherwise, an empty box (which will result in no IBGP session due to lack of IP addresses)
"""
def get_remote_ibgp_endpoint(n: Box) -> Box:
  if 'loopback' in n:
    return n.loopback

  if n.get('_daemon',False) and n.interfaces:
    return _routing.get_remote_cp_endpoint(n)

  return data.get_empty_box()

"""
build_ibgp_sessions: create IBGP session data structure

* BGP route reflectors need IBGP session with all other nodes in the same AS
* Other nodes need IBGP sessions with all RRs in the same AS
"""
def build_ibgp_sessions(node: Box, sessions: Box, topology: Box) -> None:
  node_as  = node.bgp['as']                       # Set up variables that will come handy, starting with node AS
  is_rr    = node.bgp.get("rr",None)              # Is this node an RR?
  bgp_nhs  = node.bgp.get("next_hop_self",None)   # Do we have to set next hop on IBGP sessions?
  has_ibgp = False                                # Assume we have no IBGP sessions (yet)
  rrlist = [] if is_rr else find_bgp_rr(node_as,topology)

  if is_rr or not rrlist:                         # If the current node is RR or we have a full mesh
    ibgp_ngb_list = [                             # ... we need IBGP sessions to all nodes in the AS
      ngb for ngb in topology.nodes.values()      # ... but while building the node list
        if ngb.name != node.name and              # ... skip current node
           ngb.get('bgp.as',None) == node_as]     # ... and everyone not in the current AS (or not running BGP)
  else:
    ibgp_ngb_list = rrlist

  for n in ibgp_ngb_list:
    n_intf = get_remote_ibgp_endpoint(n)
    neighbor_data = bgp_neighbor(n,n_intf,'ibgp',sessions,get_neighbor_rr(n))
    if not neighbor_data is None:
      if 'loopback' in node:
        neighbor_data._source_intf = node.loopback
      if bgp_nhs:
        neighbor_data.next_hop_self = 'ebgp'
      if is_rr and not 'rr' in neighbor_data:
        neighbor_data.rr_client = True
      node.bgp.neighbors.append(neighbor_data)
      has_ibgp = True

  if not has_ibgp:
    return

  # Do we have to warn the user that IBGP sessions work better with IGP?
  # The warning could be disabled in the settings, and we assume it doesn't make
  # sense complaining if the node has no loopback interfaces (routing on hosts)
  #
  ibgp_warning = topology.defaults.bgp.warnings.missing_igp and 'loopback' in node
  igp_list     = topology.defaults.bgp.warnings.igp_list

  if ibgp_warning:                                # Does the user want to get the warning?
    for igp in igp_list:                          # If so, check the viable IGPs
      if igp in node.module:                      # ... and if any one of them is in the list of node modules
        ibgp_warning = False                      # ... life is good, turn off the warning
        break

  if ibgp_warning:
    igp_text = f'({", ".join(igp_list)})'
    log.warning(
      text=f'Node {node.name} has IBGP sessions but no IGP',
      module='bgp',
      flag='missing_igp',
      more_hints=[ f'Add a supported IGP {igp_text} to the list of modules' ])

"""
get_interface_as -- given an interface and a node, find the real AS that would be used in an EBGP session
"""
def get_interface_as(node: Box, intf: Box) -> typing.Optional[typing.Union[int,str]]:
  return intf.get('bgp.local_as',None) or node.get('bgp.local_as',None) or node.get('bgp.as',None)

"""
build_ebgp_sessions: create EBGP session data structure

* EBGP sessions are established whenever two nodes on the same link have different AS
"""
def build_ebgp_sessions(node: Box, sessions: Box, topology: Box) -> None:
  features = devices.get_device_features(node,topology.defaults)

  #
  # Iterate over all links, find adjacent nodes
  # in different AS numbers, and create BGP neighbors
  for l in node.get("interfaces",[]):
    if 'bgp' in l and l.bgp is False:
      l.pop('bgp',None)                                               # Cleanup the flag
      continue                                                        # ... and skip interfaces with 'bgp: False'

    af_list = [ af for af in log.AF_LIST if af in l ]                 # Get interface address families
    if not af_list:                                                   # This interface has no usable address
      continue

    node_as =  node.bgp.get("as")                                     # Get our real AS number and the AS number of the peering session
    node_local_as = get_interface_as(node,l)

    intf_vrf = l.get('vrf',None)
    if node_as != node_local_as:
      if not features.bgp.local_as:
        log.error(
          text=f'{node.name} (device {node.device}) does not support BGP local AS (interface {l.name})',
          category=log.IncorrectValue,
          module='bgp')
        continue
      if intf_vrf and not features.bgp.vrf_local_as:
        log.error(
          text=f'{node.name} (device {node.device}) does not support BGP local AS for EBGP sessions in VRF {l.vrf}',
          category=log.IncorrectValue,
          module='bgp')
        continue

    for ngb_ifdata in l.get("neighbors",[]):
      af_list = [ af for af in ('ipv4','ipv6') if af in ngb_ifdata ]  # Get neighbor interface AF
      if not af_list:                                                 # Neighbor has no usable address
        continue
      #
      # Get neighbor node data and its true or interface-local AS
      #
      ngb_name = ngb_ifdata.node
      neighbor = topology.nodes[ngb_name]
      neighbor_real_as = neighbor.get('bgp.as',None)

      #
      # Check for confederations; use confederation AS towards outside peers
      #
      neighbor_c_as    = neighbor.get('bgp.confederation.as',None)
      neighbor_c_peers = neighbor.get('bgp.confederation.peers',[])
      if neighbor_c_as and neighbor_real_as!=node_local_as and node_local_as not in neighbor_c_peers:
        neighbor_real_as = neighbor_c_as

      try:                                                            # Try to get neighbor local_as
        neighbor_local_as = ( ngb_ifdata.get('bgp.local_as',None) or
                              neighbor.get('bgp.local_as',None) or
                              neighbor_real_as )
      except:                                                         # Neighbor could have bgp set to False
        neighbor_local_as = neighbor_real_as

      if not neighbor_local_as:                                       # Neighbor has no usable BGP AS number, move on
        continue

      if node_as == neighbor_real_as and node_local_as == neighbor_local_as:
        continue                                                      # Routers in the same AS + no local-as trickery => nothing to do here

      extra_data = data.get_empty_box()
      extra_data.ifindex = l.ifindex
      if 'bgp' in ngb_ifdata and isinstance(ngb_ifdata.bgp,Box):      # Copy neighbor BGP interface attributes into neighbor data
        extra_data = ngb_ifdata.bgp + extra_data                      # ... useful for things like BGP roles
      if isinstance(ngb_ifdata.get('vrf',None),str):                  # Are we attached to the neighbor's VRF?
        extra_data._vrf = ngb_ifdata.vrf

      # Figure out whether both neighbors have IPv6 LLA and/or unnumbered IPv4 interfaces
      #
      ipv4_addr = l.get('ipv4',None)
      ipv6_addr = l.get('ipv6',None)
      ipv6_lla = ipv6_addr is True and ngb_ifdata.get('ipv6',None) is True
      ipv6_num = isinstance(ipv6_addr,str) and isinstance(ngb_ifdata.get('ipv6',None),str)
      ipv4_unnum = ipv4_addr is True and ngb_ifdata.get('ipv4',None) is True
      rfc8950 = ipv4_unnum and ipv6_num                               # RFC 8950 IPv4 next hops over non-LLA EBGP

      # Sanity checks: both ends have to be numbered or unnumbered
      #
      if ipv4_addr is True and not ipv4_unnum:
        log.error(
          f'Cannot create an EBGP session between IPv4 unnumbered interface on {node.name}' + \
          f' and regular IPv4 interface on {ngb_name}',
          category=log.IncorrectValue,
          module='bgp')
        continue

      if ipv6_addr is True and not ipv6_lla:
        log.error(
          f'Cannot create an EBGP session between IPv6 LLA-only interface on {node.name}' + \
          f' and numbered IPv6 interface on {ngb_name}',
          category=log.IncorrectValue,
          module='bgp')
        continue

      if ipv4_unnum and not ipv6_num:                 # Unnumbered IPv4 without numbered IPv6
        ipv6_lla = True                               # ... requires IPv6 LLA session
        if not 'ipv6' in l:                           # ... and IPv6 enabled on the interface
          l.ipv6 = True

      if ipv6_lla:                                    # IPv6 LLA session...
        extra_data.local_if = l.ifname                # ... needs local interface name for config templates
        if ipv4_unnum:                                # And if we have unnumbered IPv4 interface
          extra_data.ipv4_rfc8950 = True              # ... we also need RFC 8950 IPv4 AF
        if not features.bgp.ipv6_lla:                 # Finally, check the IPv6_LLA feature flag
          log.error(
            text=f'{node.name} (device {node.device}) does not support EBGP sessions over auto-generated IPv6 LLA (interface {l.name})',
            category=log.IncorrectValue,
            module='bgp')
          continue

      if rfc8950:                                     # Do we have RFC 8950 IPv4 AF over numbered IPv6 session?
        extra_data.ipv4_rfc8950 = True                # Signal the need for RFC 8950 IPv4 AF
        if not features.bgp.rfc8950:                  # ... and check the feature flag
          log.error(
            text=f'{node.name} (device {node.device}) does not support IPv4 RFC 8950-style AF over regular IPv6 EBGP sessions (interface {l.name})',
            category=log.IncorrectValue,
            module='bgp')
          continue

      for k in ('local_as','replace_global_as'):      # Special handling for local-as attributes
        extra_data.pop(k,None)                        # These attributes are copied from local data, not neighbor data ==> remove neighbor data

        # Get local settings from link or node
        local_as_data = l.get(f'bgp.{k}',None) or node.get(f'bgp.{k}',None)
        if not local_as_data is None:
          extra_data[k] = local_as_data               # ... and copy it into neighbor data

      if neighbor_local_as == node_local_as:
        session_type = 'localas_ibgp'
      elif neighbor_local_as in node.get('bgp.confederation.peers',[]):
        session_type = 'confed_ebgp'
      else:
        session_type = 'ebgp'

      if session_type == 'localas_ibgp':
        if not features.bgp.local_as_ibgp:
          log.error(
            text=f'You cannot use BGP local-as to create an IBGP session with {ngb_name} on {node.name} (device {node.device})',
            category=log.IncorrectValue,
            module='bgp')
          continue

      ebgp_data = bgp_neighbor(neighbor,ngb_ifdata,session_type,sessions,extra_data)
      if not ebgp_data is None:
        ebgp_data['as'] = neighbor_local_as
        if session_type == 'localas_ibgp':
          ebgp_data.rr_client = True
          ebgp_data.next_hop_self = 'all'
        elif session_type == 'confed_ebgp':
          ebgp_data.next_hop_self = 'all'
        if intf_vrf :                                 # VRF neighbor
          if node.vrfs[l.vrf].bgp is False:           # Is BGP disabled for this VRF?
            continue                                  # ... yeah, move on
          for af in log.AF_LIST:                      # Add the 'activate' dictionary to make neighbor data consistent
            if af in ebgp_data:                       # ... as this parameter is not user-controllable
              ebgp_data.activate[af] = True           # ... enable all default AFs present on the neighbor
          data.append_to_list(node.vrfs[intf_vrf].bgp,'neighbors',ebgp_data)
        else:                                         # Global neighbor
          data.append_to_list(node.bgp,'neighbors',ebgp_data)

"""
localas_ibgp_nhs_fixup: Set 'next_hop_self' to 'all' on IBGP neighbors if a router
has at least one 'localas_ibgp' session. Also, a router with 'localas_ibgp' session
SHOULD NOT be a route reflector.

See https://blog.ipspace.net/2025/08/ibgp-local-as-rr/ (after August 29th 2025) for details
"""
def localas_ibgp_nhs_fixup(node: Box,topology: Box) -> None:
  ngb_list = node.bgp.get('neighbors',None)
  if not ngb_list:                                    # No neighbors, no worries ;)
    return

  localas_ibgp_list = [ ngb for ngb in ngb_list if ngb.type == 'localas_ibgp' ]
  if not localas_ibgp_list:                           # No localas_ibgp sessions, no worries
    return

  for ngb in ngb_list:                                # We have at least one localas_ibgp session
    if ngb.type != 'ibgp':                            # Now we have to iterate over all true IBGP neighbors
      continue
    ngb.next_hop_self = 'all'                         # And enable next-hop-self on all routes

  if node.get('bgp.rr',None):
    log.warning(
      text='{node.name} has a local-as IBGP session and SHOULD NOT be a route reflector',
      module='bgp',
      flag='localas_ibgp_rr')

"""
activate_bgp_default_af -- activate default AF on IPv4 and/or IPv6 transport sessions

Based on transport session(s) with a BGP neighbor, local BGP AF, and BGP AF configuration
parameters, set neighbor.activate.AF flags
"""

def activate_bgp_default_af(node: Box, activate: Box, topology: Box) -> None:
  for ngb in node.bgp.neighbors:
    for af in ('ipv4','ipv6'):
      if af in ngb:
        ngb.activate[af] = node.bgp.get(af) and af in activate and ngb.type in activate[af]

"""
Build BGP route reflector clusters

Iterate over all ASNs in the lab, and for route reflectors that don't have rr_cluster_id
defined, find an AS-wide cluster ID: the lowest BGP router ID of all route reflectors
(members of rr_list) that don't have rr_cluster_id set (because those obviously want to be left alone)
"""
def build_bgp_rr_clusters(topology: Box) -> None:
  # Build a list of autonomous systems in the lab
  as_list = set( n.bgp['as'] for n in topology.nodes.values() if 'bgp' in n and 'as' in n.bgp )

  for asn in as_list:
    rrlist = find_bgp_rr(asn,topology)
    if not rrlist:                        # No BGP route reflectors in this ASN
      continue

    # Build a list of RR cluster candidates: router IDs of route reflectors that don't
    # have an explicit rr_cluster_id
    #
    # The shared cluster ID will be the minimum value from that list
    #
    rr_cluster_candidates = [n.bgp.router_id for n in rrlist if not 'rr_cluster_id' in n.bgp]
    rr_cluster_id = None
    if rr_cluster_candidates:
      rr_cluster_id = min(rr_cluster_candidates)

    # Now iterate over the route reflectors and either set the shared cluster ID
    # or validate that the static cluster ID is an IPv4 address
    #
    for n in rrlist:
      if not 'rr_cluster_id' in n.bgp:
        n.bgp.rr_cluster_id = rr_cluster_id or n.bgp.router_id

"""
build_bgp_sessions: create BGP session data structure

* Create an empty list of BGP neighbors
* Create IBGP sessions
* Create EBGP sessions
* Set BGP AF flags
"""

def build_bgp_sessions(node: Box, topology: Box) -> None:
  if not isinstance(node.get('bgp',None),Box) or not node.get('bgp.as',None):   # Sanity check
    log.fatal(
      f'build_bgp_sessions: node {node.name} has no usable BGP AS number, how did we get here???',
      module='bgp',
      header=True)
    return                                                                      # ... it's insane, get out of here

  node.bgp.neighbors = []
  bgp_sessions = node.bgp.get('sessions') or data.get_box(BGP_DEFAULT_SESSIONS)
  if not validate_bgp_sessions(node,bgp_sessions,'sessions'):
    return

  build_ibgp_sessions(node,bgp_sessions,topology)
  build_ebgp_sessions(node,bgp_sessions,topology)
  localas_ibgp_nhs_fixup(node,topology)

  # Calculate BGP address families
  #
  for af in ['ipv4','ipv6']:
    for n in node.bgp.neighbors:
      if af in n:
        node.bgp[af] = True
        break

  # Activate default BGP address families
  features = devices.get_device_features(node,topology.defaults)
  if 'activate' in node.bgp:
    if not features.bgp.activate_af:
      log.error(
        f'node {node.name} (device {node.device}) does not support configurable activation of default BGP address families',
        log.IncorrectValue,
        'bgp')
      return

  activate = node.bgp.get('activate') or data.get_box(BGP_DEFAULT_SESSIONS)
  if not validate_bgp_sessions(node,activate,'activate'):
    return

  activate_bgp_default_af(node,activate,topology)

"""
bgp_set_advertise: set bgp.advertise flag on stub links and on loopback interfaces
"""
def bgp_set_advertise(node: Box, topology: Box) -> None:
  stub_roles = data.get_global_parameter(topology,"bgp.advertise_roles") or []

  # Process regular interfaces and the loopback interface (if it exists)
  #
  for l in node.get("interfaces",[]) + ([ node.loopback ] if 'loopback' in node else []):
    if "bgp" in l:
      if l.bgp is False:                    # Skip interfaces on which we don't want to run BGP
        continue
      if "advertise" in l.bgp:              # Skip interfaces that already have the 'advertise' flag
        continue

    role = l.get("role",None)               # Get interface/link role
    if l.get("type",None) in stub_roles or role in stub_roles:
      # We have a potential stub link according to advertised_roles, but we still have to check for true stub
      #
      if role != "stub":
        l.bgp.advertise = True              # No problem if the role is not stub
      else:                                 # Otherwise figure out whether it's a true stub
        l.bgp.advertise = _routing.is_true_stub(l,topology)
      continue                              # And move on

    if l.get('type',None) == 'loopback' and node.bgp.advertise_loopback:
      l.bgp.advertise = True                # ... also advertise loopback prefixes if bgp.advertise_loopback is set

"""
bgp_set_originate_af: set bgp[af] flags based on prefixes that should be originated
"""

def bgp_set_originate_af(node: Box, topology: Box) -> None:
  if 'bgp' not in node:                                     # Safeguard: skip non-BGP nodes
    return

  if node.get('bgp.originate',[]):                          # bgp.originate attribute implies IPv4 is active
    node.bgp.ipv4 = True
    pfxs = topology.get('prefix',{})
    for o_idx,o_value in enumerate(node.bgp.originate):     # Also, replace named prefixes with IPv4 values
      if o_value in pfxs:
        if 'ipv4' not in pfxs[o_value]:
          log.error(
            f'Named prefix {o_value} used in bgp.originate in node {node.name} must have IPv4 component',
            category=log.MissingValue,
            module='bgp')
          continue
        node.bgp.originate[o_idx] = pfxs[o_value].ipv4

  for af in ['ipv4','ipv6']:
    if node.get(f'bgp.{af}',False):                         # No need for further checks if the AF flag is already set
      continue

    if node.get('bgp.advertise_loopback',True):             # If the router advertises its loopback prefix
      if af in node.get('loopback',{}):                     # ... do the AF checks on loopback interface
        node.bgp[af] = True
        continue

    for intf in node.get("interfaces",[]):                  # No decision yet, iterate over all interfaces
      if af in intf and intf[af]:                           # Is the address family active on the interface?
        if intf.get('bgp.advertise',False):                 # Is the interface prefix advertised in BGP?
          if not 'vrf' in intf:                             # The AF fix is only required for global interfaces
            node.bgp[af] = True                             # ... the stars have aligned, set the BGP AF flag

"""
process_as_list:
  If the global BGP parameters have as_list attribute, set node AS numbers and node
  RR flags accordingly

This function is called from init_groups very early in the topology initialization process
and has to do its own data validation.
"""
def process_as_list(topology: Box) -> None:
  if not topology.get('bgp.as_list'):       # Do we have global bgp.as_list setting?
    return                                  # ... nope, no work for me ;))

  if not validate_item(                     # Do data validation on bgp.as_list
            parent=topology.bgp,
            key='as_list',
            data_type=topology.defaults.bgp.attributes.as_list,
            parent_path='bgp',
            data_name='BGP as_list',
            module='bgp',
            module_source='topology',
            topology=topology,
            attr_list=[ 'bgp' ],
            attributes=topology.defaults.attributes,
            enabled_modules=[]):
    return

  if log.pending_errors():                  # Stop processing on validation errors
    return

  # Utility function: expand an as_list element using regexp or wildcard expressions
  #
  def expand_element(as_data: Box, asn: str, e_name: str) -> list:
    return groups.expand_group_members(
              g_members=as_data[e_name],
              g_objects=topology.nodes,
              g_list=[],
              g_name=e_name,
              g_type=f'bgp.as_list.{asn}',
              g_prune=False)

  node_data = data.get_empty_box()
  for asn,as_data in topology.bgp.as_list.items():
    as_data.members = expand_element(as_data,asn,'members')
    for n in as_data.members:
      if 'as' in node_data[n]:
        log.error(
          text=f"BGP module supports at most 1 AS per node; {n} is already member of {node_data[n]['as']} and cannot also be part of {asn}",
          category=log.IncorrectValue,
          module='bgp')
        continue
      node_data[n]["as"] = asn

    if 'rr' in as_data:
      as_data.rr = expand_element(as_data,asn,'rr')

    for n in as_data.get('rr',[]):
      if node_data.get(f'{n}.as',None) != asn:
        log.error(
          text=f"Node {n} is specified as route reflector in AS {asn} but is not in member list",
          category=log.IncorrectValue,
          module='bgp')
        continue
      node_data[n].rr = True

  for name,node in topology.nodes.items():
    if name in node_data:
      node_as = node.bgp.get("as",None)
      if node_as and node_as != node_data[name]["as"]:
        log.error(
          text=f'Node {node.name} has AS {node_as} but is also in member list of AS {node_data[node.name]["as"]}',
          category=log.IncorrectValue,
          module='bgp')
        continue

      node.bgp = node_data[name] + node.bgp

"""
Check the confederation data (if it exists) against node AS numbers
"""
def check_confederation_data(topology: Box) -> None:
  if 'bgp.confederation' not in topology:
    return

  rev_map: dict = {}
  bgp_confed = topology.bgp.confederation
  for c_asn,c_data in bgp_confed.items():
    if not c_data.members:
      log.error(
        f'Confederation AS {c_asn} needs at least one member ASN',
        category=log.MissingValue,
        module='bgp')
    for cm_asn in c_data.members:
      if cm_asn in rev_map:
        log.error(
          f'Confederation member {cm_asn} is in confederations {c_asn} and {rev_map[cm_asn]}',
          more_hints="While that's a valid BGP design, netlab does not support it",
          category=log.IncorrectValue,
          module='bgp')
      rev_map[cm_asn] = c_asn
      if cm_asn in bgp_confed:
        log.error(
          f'Confederation member AS {cm_asn} (part of AS {c_asn}) is itself also a confederation AS',
          category=log.IncorrectValue,
          module='bgp')

  for ndata in topology.nodes.values():
    if 'bgp.as' not in ndata:
      continue
    n_as = ndata.bgp['as']
    if n_as in bgp_confed:
      log.error(
        f'Node {ndata.name} is using confederation ASN {n_as}',
        more_hints='BGP speakers can use only confederation member ASNs, not the confederation ASN',
        category=log.IncorrectValue,
        module='bgp')
    if n_as not in rev_map:
      continue

    c_as = rev_map[n_as]
    d_features = devices.get_device_features(ndata,topology.defaults)
    if not d_features.get('bgp.confederation',False):
      log.error(
        f'Node {ndata.name} (device {ndata.device}) uses member ASN {n_as} of confederation AS {c_as}',
        more_hints=f'Device {ndata.device} does not support BGP confederations',
        category=log.IncorrectType,
        module='bgp')
      continue

    ndata.bgp.confederation['as'] = c_as
    ndata.bgp.confederation.peers = [ asn for asn in bgp_confed[c_as].members if asn != n_as ]

"""
bgp_transform_community_list: transform _netlab_ community keywords into device keywords
"""
def bgp_transform_community_list(node: Box, topology: Box) -> None:
  global BGP_DEFAULT_COMMUNITY_KW,BGP_INHERIT_COMMUNITY

  clist = node.get('bgp.community')
  if not clist:
    return
  
  features = devices.get_device_features(node,topology.defaults)
  kw_xform = features.get('bgp.community') or BGP_DEFAULT_COMMUNITY_KW

  for s_type in list(clist.keys()):
    kw_list = clist[s_type]
    for kw in kw_list:
      if not kw in kw_xform:
        log.error(
          f"Invalid {s_type} BGP community propagation keyword '{kw}' for device {node.device}/node {node.name}",
          category=log.IncorrectValue,
          module='bgp',
          more_hints=[ f"Valid values are {','.join(kw_xform.keys())}" ])
    
  for i_kw in BGP_INHERIT_COMMUNITY:            # Finally, set up the missing community propagation values
    if i_kw not in clist:                       # for rare BGP session types
      clist[i_kw] = clist[BGP_INHERIT_COMMUNITY[i_kw]]

  for s_type in list(clist.keys()):
    clist[s_type] = data.kw_list_transform(kw_xform,clist[s_type])

"""
While figuring out the BGP link role, we're also collecting the BGP attributes
configured on relevant objects (links, interfaces, VLANs). We'll then use
the collected attributes to generate a warning if a BGP attribute is used
on an intra-AS link.
"""
def collect_bgp_attr(attr: Box, obj: Box, o_name: typing.Optional[str] = None) -> None:
  if 'bgp' not in obj:
    return
  if not isinstance(obj.bgp,Box):
    return
  
  for k in obj.bgp.keys():
    data.append_to_list(attr,k,o_name)

"""
If we have BGP link/interface attributes on an object that is not an inter-AS
link (or VLAN), we might have to generate a warning
"""
def warn_bgp_attributes(o_name: str, o_type: str, attr: Box, topology: Box) -> None:
  bgp_attr = topology.defaults.bgp.attributes.link          # Get BGP link attributes
  for a_name in list(attr.keys()):
    if a_name.startswith('_'):                              # Remove internal attributes
      attr.pop(a_name,None)
    elif bgp_attr.get(f'{a_name}._intra_as',None):          # ... and attributes that can appear on intra-as links
      attr.pop(a_name,None)

  if not attr:                                              # No other attributes?
    return                                                  # ... cool, we're done

  m_data = []
  for a_name,a_list in attr.items():
    a_filter = [ n for n in a_list if n ]
    if a_filter:
      m_data.append(f'bgp.{a_name} used on node(s) {",".join(a_filter)}')
  
  log.warning(
    text=f'You cannot use BGP attribute(s) {",".join(attr)} on intra-AS {o_type} {o_name}',
    more_data=m_data,
    module='bgp',
    flag='intra_as_attr')

"""
link_ebgp_role_set -- set EBGP role for a regular link
"""
def ebgp_role_link(link: Box, topology: Box, EBGP_ROLE: str) -> None:
  as_set = {}
  attr_set = data.get_empty_box()
  collect_bgp_attr(attr_set,link)
  for ifdata in link.get('interfaces',[]):                  # Collect BGP AS numbers from nodes
    collect_bgp_attr(attr_set,ifdata,ifdata.node)
    ndata = topology.nodes[ifdata.node]                     # ... connected to the link
    node_as = ndata.get('bgp.as',None)                      # Consider real node AS and
    if node_as:                                             # node/interface local-as
      as_set[node_as] = True                                # when building set of AS on the link
    intf_as = get_interface_as(ndata,ifdata)                # That makes sure the ibgp_localas link is still external
    if intf_as:
      as_set[intf_as] = True                                # ... and store collected AS numbers in a dictionary

  if len(as_set) > 1:                                       # If we have more than two AS numbers per link
    if not link.get("role",None):                           # ... we set the link role unless it's already set
      link.role = EBGP_ROLE
  elif attr_set:                                            # Generate a warning for BGP attributes on intra-AS link
    warn_bgp_attributes(link._linkname,'link',attr_set,topology)

"""
vlan_ebgp_role_collect -- collect EBGP role information from a VLAN link
"""
def vlan_ebgp_role_collect(link: Box, topology: Box) -> None:
  vlan_name = link.get('vlan_name',None)                    # Get the relevant VLAN name
  if vlan_name not in topology.vlans:                       # Not a global VLAN, don't waste time
    return

  vdata = topology.vlans[vlan_name]
  if not '_bgp_attr' in vdata:                              # The first time we're encountering a VLAN...
    collect_bgp_attr(vdata._bgp_attr,vdata)                 # ... collect global VLAN BGP attributes
  for ifdata in link.get('interfaces',[]):                  # Iterate over nodes attached to this VLAN segment
    ndata = topology.nodes[ifdata.node]
    n_vdata = ndata.get(f'vlans.{vlan_name}',{})            # Get node VLAN data (if any)
    collect_bgp_attr(vdata._bgp_attr,n_vdata,ifdata.node)   # ... and scan it for BGP attributes
    node_as = ndata.get('bgp.as',None)                      # As above, consider real node AS
    if node_as:
      data.append_to_list(topology.vlans[vlan_name],'_as_set',node_as)
    intf_as = get_interface_as(ndata,ifdata)                # ... and node/interface local AS
    if intf_as:
      data.append_to_list(topology.vlans[vlan_name],'_as_set',intf_as)

"""
vlan_ebgp_role_set -- set EBGP role on VLANs based on collected information
"""
def vlan_ebgp_role_set(topology: Box, EBGP_ROLE: str) -> None:
  for vname,vdata in topology.vlans.items():                # Iterate over global VLANs
    if len(vdata._as_set) > 1:                              # Did we collect at least two ASNs for the VLAN
      if 'role' not in vdata:                               # ... and the VLAN has no role?
        vdata.role = EBGP_ROLE                              # ... set VLAN role to EBGP role
    elif vdata._bgp_attr:                                   # Not an inter-AS link. Does it have BGP attributes?
      warn_bgp_attributes(vname,'vlan',vdata._bgp_attr,topology)

    vdata.pop('_as_set',None)                               # ... and clean up
    vdata.pop('_bgp_attr',None)

"""
Make sure BGP data always has the expected attributes (currently: neighbors, might be others in the future)
"""
def sanitize_bgp_data(node: Box) -> None:
  for (b_data,_,_) in _rp_utils.rp_data(node,'bgp'):
    if 'neighbors' not in b_data:
      b_data.neighbors = []

class BGP(_Module):
  def module_normalize(self, topology: Box) -> None:
    setup_bgp_constants(topology)

  """
  Node pre-transform: set bgp.rr node attribute to _true_ if the node name is in the
  global bgp.rr attribute. Also, delete the global bgp.rr attribute so it's not propagated
  down to nodes
  """
  def node_pre_transform(self, node: Box, topology: Box) -> None:
    if "rr_list" in topology.get("bgp",{}):
      if node.name in topology.bgp.rr_list:
        node.bgp.rr = True

    check_bgp_parameters(node, topology)

  """
  pre-link transform processing handles VLANs. An AS set is built for every VLAN
  and the VLAN role is set when a VLAN contains nodes from more than one AS.
  """
  def module_pre_link_transform(self, topology: Box) -> None:
    EBGP_ROLE = topology.bgp.get("ebgp_role",None) or topology.defaults.bgp.get("ebgp_role",None)
    if not EBGP_ROLE:
      return

    has_vlans = 'vlan' in topology.module and 'vlans' in topology
    for link in topology.links:
      if not 'vlan_name' in link:
        ebgp_role_link(link,topology,EBGP_ROLE)
      elif has_vlans:
        vlan_ebgp_role_collect(link,topology)

    if has_vlans:
      vlan_ebgp_role_set(topology,EBGP_ROLE)

  #
  # Have to set BGP router IDs, cluster IDs, and confederation data before going into node_post_transform
  #
  def module_post_transform(self, topology: Box) -> None:
    for n in topology.nodes.values():
      if 'bgp' in n:
        _routing.router_id(n,'bgp',topology.pools)

    build_bgp_rr_clusters(topology)
    check_confederation_data(topology)

  #
  # Execute the rest of node post-transform code, including setting up the BGP session table
  #
  def node_post_transform(self, node: Box, topology: Box) -> None:
    if not "bgp" in node:   # pragma: no cover (this should have been caught in check_bgp_parameters)
      log.fatal(f"Internal error: node {node.name} has BGP module enabled but no BGP parameters","bgp")
      return
    build_bgp_sessions(node,topology)
    bgp_set_advertise(node,topology)
    bgp_set_originate_af(node,topology)
    _routing.remove_vrf_routing_blocks(node,'bgp')
    bgp_transform_community_list(node,topology)
    _routing.check_vrf_protocol_support(node,'bgp',None,'bgp',topology)
    _routing.process_imports(node,'bgp',topology,global_vars.get_const('vrf_igp_protocols',['connected']))
    sanitize_bgp_data(node)
