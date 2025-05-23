#
# BGP transformation module
#
import typing

import re
from box import Box

from . import _Module,_routing
from .. import data
from ..data import global_vars
from ..data.types import must_be_int,must_be_list,must_be_asn
from ..data.validate import validate_item
from ..augment import devices
from ..utils import log, routing as _rp_utils

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
          valid_values=topology['defaults.bgp.attributes.global.community.ibgp'],
          module='bgp')

BGP_VALID_AF: typing.Final[list] = ['ipv4','ipv6']
BGP_VALID_SESSION_TYPE: typing.Final[list] = ['ibgp','ebgp','localas_ibgp']

def validate_bgp_sessions(node: Box, sessions: Box, attribute: str) -> bool:
  OK = True
  for k in list(sessions.keys()):
    if not k in BGP_VALID_AF:
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
  rrlist = find_bgp_rr(node.bgp.get("as"),topology)
  has_ibgp     = False                            # Assume we have no IBGP sessions (yet)

  # If we don't have route reflectors, or if the current node is a route
  # reflector, we need BGP sessions to all other nodes in the same AS
  if not(rrlist) or node.bgp.get("rr",None):
    for name,n in topology.nodes.items():
      if "bgp" in n:
        if n.bgp.get("as") == node.bgp.get("as") and n.name != node.name:
          n_intf = get_remote_ibgp_endpoint(n)
          neighbor_data = bgp_neighbor(n,n_intf,'ibgp',sessions,get_neighbor_rr(n))
          if not neighbor_data is None:
            if 'loopback' in node:
              neighbor_data._source_intf = node.loopback
            node.bgp.neighbors.append(neighbor_data)
            has_ibgp = True

  #
  # The node is not a route reflector, and we have a non-empty RR list
  # We need BGP sessions with the route reflectors
  else:
    for n in rrlist:
      if n.name != node.name:
        n_intf = get_remote_ibgp_endpoint(n)
        neighbor_data = bgp_neighbor(n,n_intf,'ibgp',sessions,get_neighbor_rr(n))
        if not neighbor_data is None:
          if 'loopback' in node:
            neighbor_data._source_intf = node.loopback
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

      session_type = 'localas_ibgp' if neighbor_local_as == node_local_as else 'ebgp'
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

BGP_DEFAULT_SESSIONS: typing.Final[dict] = {
  'ipv4': [ 'ibgp', 'ebgp', 'localas_ibgp' ],
  'ipv6': [ 'ibgp', 'ebgp', 'localas_ibgp' ]
}

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

  for l in node.get("interfaces",[]):
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

  if not validate_item(
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

  if log.pending_errors():
    return

  node_data = data.get_empty_box()
  for asn,as_data in topology.bgp.as_list.items():
    for n in as_data.members:
      if 'as' in node_data[n]:
        log.error(
          text=f"BGP module supports at most 1 AS per node; {n} is already member of {node_data[n]['as']} and cannot also be part of {asn}",
          category=log.IncorrectValue,
          module='bgp')
        continue
      node_data[n]["as"] = asn

    for n in as_data.get('rr',{}):
      if node_data[n]["as"] != asn:
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

BGP_DEFAULT_COMMUNITY_KW: typing.Final[dict] = {
  'standard': 'standard',
  'extended': 'extended'
}

"""
bgp_transform_community_list: transform _netlab_ community keywords into device keywords
"""
def bgp_transform_community_list(node: Box, topology: Box) -> None:
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
    
  if 'localas_ibgp' not in clist:
    clist.localas_ibgp = clist.ibgp

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

class BGP(_Module):
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
  # Have to set BGP router IDs and cluster IDs before going into node_post_transform
  #
  def module_post_transform(self, topology: Box) -> None:
    for n in topology.nodes.values():
      if 'bgp' in n:
        _routing.router_id(n,'bgp',topology.pools)

    build_bgp_rr_clusters(topology)

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
