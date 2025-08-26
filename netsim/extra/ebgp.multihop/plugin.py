import ipaddress

from box import Box

from netsim import api
from netsim.augment import devices, links
from netsim.data.validate import validate_attributes
from netsim.modules import vrf
from netsim.utils import log
from netsim.utils import routing as _bgp

_config_name = 'ebgp.multihop'
_execute_after = [ 'ebgp.utils', 'bgp.session' ]
_requires    = [ 'bgp' ]

def pre_link_transform(topology: Box) -> None:
  if not 'multihop' in topology.get('bgp',{}):
    return

  # Find relevant modules for session attributes
  v_mods = [ m for m in topology.module if m in ['bgp','vrf']]

  sessions = links.adjust_link_list(topology.bgp.multihop.sessions,topology.nodes,'bgp.multihop[{link_cnt}]')
  topology.bgp.multihop.sessions = sessions
  next_linkindex = links.get_next_linkindex(topology)
  for s in sessions:
    for attr in list(s.keys()):                       # Change session attributes into BGP link attributes
      # Skip internal attributes and BGP/VRF attributes already within BGP namespace
      if attr in ['interfaces','_linkname','bgp','vrf']:    
        continue
      s.bgp[attr] = s[attr]                           # Turn a session attribute into 'bgp.x' attribute
      s.pop(attr,None)
    
    s.type = 'tunnel'
    s.linkindex = next_linkindex
    next_linkindex += 1
    s._phantom_link = True

    validate_attributes(
      data=s,                                         # Validate pseudo-link data
      topology=topology,
      data_path=s._linkname,
      data_name=f'EBGP session',
      attr_list=['link'],                             # We're checking link attributes
      modules=v_mods,                                 # ... against BGP and VRF parameters
      module_source='topology',
      module='ebgp.multihop')                         # Validation is called from 'ebgp.multihop' plugin

    for intf in s.interfaces:
      node = topology.nodes[intf.node]
      for attr in list(intf.keys()):                  # Change interface attributes into BGP attributes
        if attr in ['node','bgp','vrf']:              # Skip internal attributes and attributes already in BGP/VRF namespace
          continue
        intf.bgp[attr] = intf[attr]                   # Turn an interface attribute into 'bgp.x' attribute
        intf.pop(attr,None)

      validate_attributes(
        data=intf,                                    # Validate interface data
        topology=topology,
        data_path=f'{s._linkname}.{intf.node}',
        data_name=f'BGP neighbor',
        attr_list=['interface','link'],               # We're checking interface or link attributes
        modules=v_mods,                               # ... against BGP/VRF attributes
        module_source='topology',
        module='ebgp.multihop')                       # Function is called from 'ebgp.multihop' plugin

      if not 'loopback' in node:
        log.error(
          'Cannot establish EBGP multihop session from node {intf.name}: node has no loopback interface',
          log.IncorrectValue,'ebgp.multihop')
        continue
      for af in ['ipv4','ipv6']:
        if af in node.loopback:
          intf[af] = node.loopback[af]
      intf.bgp.multihop = 255
      if 'vrf' in intf:
        intf.bgp._vrf = intf.vrf
      intf._mh_bgp_session = True
      intf._phantom_link = True
      intf.ifname = f'_ebgp_multihop_{s.linkindex}'

  topology.links.extend(sessions)

'''
check_device_support -- check whether the device used in a multihop EBGP session supports it
'''
def check_multihop_support(ndata: Box, topology: Box) -> None:
  features = devices.get_device_features(ndata,topology.defaults)
  if features.bgp.get('multihop',None):
    return
  
  log.error(
    f'EBGP multihop is not supported by node {ndata.name} (device {ndata.device})',
    log.IncorrectValue,'ebgp.multihop')

'''
check_af_activation_support -- check whether the device used in a multihop EBGP session supports per-af activation
'''
def check_af_activation_support(ndata: Box, topology: Box) -> None:
  features = devices.get_device_features(ndata,topology.defaults)
  if features.bgp.get('activate_af',None):
    return
  
  log.error(
    f'Selective BGP address family activation is not supported by node {ndata.name} (device {ndata.device})',
    log.IncorrectValue,'ebgp.multihop')

'''
augment_af_activation -- change the address families active on EBGP multihop sessions
'''
def augment_af_activation(ndata: Box, topology: Box) -> None:
  af_set = ndata.get('bgp.multihop.activate',None) or topology.get('bgp.multihop.activate',None)
  af_list_base = topology.defaults.bgp.attributes['global'].multihop.activate

  if not af_set:
    return

  check_af_activation_support(ndata,topology)
  for ngb in _bgp.neighbors(ndata,vrf=True,select=['ebgp','localas_ibgp']):
    if not 'multihop' in ngb:                                     # Skip regular neighbors
      continue
    for af in ['ipv4','ipv6']:                                    # A neighbor could be an IPv4 or IPv6 neighbor
      if not af in ngb:                                           # Skip the irrelevant transport AF
        continue
      for bgp_af in af_list_base[af].valid_values:                # Iterate over all potential address famiilies
        chg = ngb.activate if bgp_af in ['ipv4','ipv6'] else ngb  # Find the object to change (neighbor or activate dictionary)
        if bgp_af in af_set[af]:                                  # Is the AF active on this transport EBGP multhop session?
          chg[bgp_af] = True                                      # Yes, turn it on
        else:
          chg.pop(bgp_af,None)                                    # Otherwise remove it

'''
Check whether a node has EBGP multihop sessions
'''
def ebgp_multihop_sessions(ndata: Box, topology: Box) -> bool:
  mh_intf = [ intf for intf in ndata.interfaces if intf.get('_mh_bgp_session',False) ]
  if not mh_intf:                                 # Do we have any fake interfaces for MH EBGP sessions?
    return False

  check_multihop_support(ndata,topology)          # Check that the node supports it
  api.node_config(ndata,_config_name)             # We must have some multihop sessions, add extra config
  augment_af_activation(ndata,topology)           # ... and activate relevant address families on these sessions
  return True

'''
fix_vrf_loopbacks:

* Change the source interface for VRF EBGP sessions
* Change the neighbor IP address if the remote end is in a VRF
'''
def fix_vrf_loopbacks(ndata: Box, topology: Box) -> None:
  features = devices.get_device_features(ndata,topology.defaults)
  for ngb in _bgp.neighbors(ndata,vrf=True,select=['ebgp','localas_ibgp']):    # Iterate over all EBGP and localas_ibgp neighbors
    if not ngb.get('multihop',None):                            # Not a multihop session, move on
      continue
    if '_vrf' in ngb:                                           # Is the neighbor endpoint in a VRF?
      lb = vrf.get_vrf_loopback(topology.nodes[ngb.name],ngb._vrf)
      if not lb:                                                # Did we get the remote VRF loopback?
        continue                                                # If not, we expect the remote end to throw an error
      for af in ('ipv4','ipv6'):                                # Now copy remote VRF loopback IPv4/IPv6 address
        ngb.pop(af)                                             # ... into neighbor data
        if af in lb:                                            # ... removing whatever might have come from the
          ngb[af] = str(ipaddress.ip_interface(lb[af]).ip)      # ... global loopback

    if '_src_vrf' in ngb:                                       # Is our endpoint in a VRF?
      if not isinstance(features.bgp.multihop,Box) or features.bgp.multihop.vrf is not True:
        log.error(
          f'Device {ndata.device} does not support VRF EBGP multihop sessions (node {ndata.name}, VRF {ngb._src_vrf})',
          category=log.IncorrectValue,
          module='ebgp.multihop')
        continue

      lb = vrf.get_vrf_loopback(ndata,ngb._src_vrf)             # Find local VRF loopback
      if not lb:                                                # Now we MUST have a loopback
        log.error(
          f'Cannot create EBGP multihop session to {ngb.name} from VRF {ngb._src_vrf} on {ndata.name}',
          more_hints=['A VRF with a multihop EBGP session must have a loopback interface'],
          category=log.MissingValue,
          module='ebgp.multihop')
        continue

      ngb._source_intf = lb

    else:
      ngb._source_intf = ndata.loopback

'''
post_transform processing:

* Remove fake interfaces and links
* Check device (= template) support
* Augment address family activation
'''
def post_transform(topology: Box) -> None:
  global _config_name
  for ndata in topology.nodes.values():
    if ebgp_multihop_sessions(ndata,topology):
      fix_vrf_loopbacks(ndata,topology)

'''
Cleanup: remove interfaces and links with _phantom_link flag
'''
def cleanup(topology: Box) -> None:
  for ndata in topology.nodes.values():
    ndata.interfaces = [ intf for intf in ndata.interfaces if not intf.get('_phantom_link',None) ]

  topology.links = [ link for link in topology.links if not link.get('_phantom_link',None) ]
