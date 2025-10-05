#
# VRF module
#
import ipaddress
import typing

from box import Box

from ..augment import addressing, devices, groups, links
from ..data import get_box, global_vars
from ..data.types import must_be_list
from ..data.validate import validate_attributes
from ..utils import log
from . import _dataplane, _Module, _routing, get_effective_module_attribute, remove_module

#
# get_node_vrf_data: an abstraction layer that returns node-level VRF data structure
# as it would appear after the node_post_transform hook
#
# You have to use this function instead of 'node or global data' logic whenever you need
# node VRF data before VRF node_post_transform hook is executed
#

def get_node_vrf_data(vname: str, node: Box, topology: Box) -> typing.Optional[Box]:
  topo_data = topology.get('vrfs').get(vname,None)    # Get global VRF data (or none if there's no global data)
  if not vname in node.get('vrfs',{}):                # If there's no node VRF data
    return topo_data                                  # ... return global value whatever it is
  else:
    node_data = node.vrfs[vname]                      # We have some node VRF data, and we assume it's a Box
    topo_data = topo_data or {}                       # Global data must be a dict/Box or the merge will fail
    return topo_data + node_data                      # Now merge global+node data
                                                      # ... note that the result will always be a Box

#
# Initialize global data structures needed for ID/RD allocation
#

def init_vrf_static_ids(topology: Box) -> None:
  for k in ('id','rd'):
    _dataplane.create_id_set(f'vrf_{k}')

  _dataplane.set_id_counter('vrf_id',1,4095)

#
# Populate the global ID/RD/RT data structures with preconfigured global- and node VRF data
#
def populate_vrf_static_ids(topology: Box) -> None:
  for k in ('id','rd'):
    _dataplane.extend_id_set(f'vrf_{k}',_dataplane.build_id_set(topology,'vrfs',k,'topology'))

  for n in topology.nodes.values():
    for k in ('id','rd'):
      _dataplane.extend_id_set(f'vrf_{k}',_dataplane.build_id_set(n,'vrfs',k,f'nodes.{n.name}'))

#
# Get a usable AS number. Try bgp.as then vrf.as from node and global settings
#
def get_rd_as_number(obj: Box, topology: Box) -> typing.Optional[typing.Any]:
  return (
    obj.get('bgp.as',None) or
    obj.get('vrf.as',None) or
    topology.get('bgp.as',None) or
    topology.get('vrf.as',None) )

#
# Parse rd/rt value -- check whether the RD/RT value is in N:N format
#

def parse_rdrt_value(value: str) -> typing.Optional[typing.List[typing.Union[int,str]]]:
  try:
    (asn,vid) = str(value).split(':')
  except Exception:
    return None

  try:
    return [int(asn),int(vid)]
  except Exception:
    try:
      ipaddress.IPv4Address(asn)
      return [asn,int(vid)]
    except Exception:
      return None

def get_next_vrf_id(asn: str) -> typing.Tuple[int,str]:
  rd_set = _dataplane.get_id_set('vrf_rd')
  id_set = _dataplane.get_id_set('vrf_rd')
  while True:
    vrf_id = _dataplane.get_next_id('vrf_id')
    if not f'{asn}:{vrf_id}' in rd_set:
      break

  rd = f'{asn}:{vrf_id}'
  rd_set.add(rd)
  id_set.add(vrf_id)
  return (vrf_id,rd)

"""
Validate VRF loopback data:

* Skip the validation check if the loopback instance is not a box (must be bool)
* Check against 'loopback' data type
* Global VRF loopback definition MUST NOT have ipv4/ipv6 values
"""
def validate_vrf_loopback(vname: str,vdata: Box,obj: Box,topology: Box) -> None:
  lb = vdata.loopback
  if not isinstance(lb,Box):
    return
  if obj is topology and ('ipv4' in lb or 'ipv6' in lb):
    log.error(f'IP prefix for VRF loopbacks can only be specified in node VRF data (found in global VRF {vname})',
    more_hints=[ 'Use pool attribute or specify the VRF loopback ipv4/ipv6 address in the node VRF data'],
    category=log.IncorrectAttr,
    module='vrf')

  obj_path = f'vrfs.{vname}' if obj is topology else f'nodes.{obj.name}.vrfs.{vname}'
  validate_attributes(
    data=lb,                                      # Validate loopback data
    topology=topology,
    data_path=f'{obj_path}.loopback',             # Topology path to VRF loopback
    data_name=f'loopback',
    attr_list=['loopback','link','interface'],    # We're checking loopback attributes
    modules=obj.get('module',[]),                 # ... against topology/node modules
    module_source=f'topology' if obj is topology else f'nodes.{obj.name}',
    module='vrf')                                 # Function is called from 'vrf' module

"""
Normalize and further validate VRF dictionaries (the initial data type sanity
checks have been done by topology/node validation module):

* Replace None values with empty dictionaries
* Check for reserved VRF names
* Validate VRF loopback data
* Set the RD value
"""

def normalize_vrf_dict(obj: Box, topology: Box) -> None:
  if not 'vrfs' in obj:
    return

  asn = None
  obj_name = 'global VRFs' if obj is topology else obj.name

  for vname in list(obj.vrfs.keys()):
    if obj.vrfs[vname] is None:
      obj.vrfs[vname] = {}

    vdata = obj.vrfs[vname]
    if vname in topology.defaults.vrf.attributes.reserved:
      r_list = ','.join(sorted(topology.defaults.vrf.attributes.reserved))
      log.error(
        f"Cannot use VRF {vname} in {obj_name} to avoid confusion with vendor built-in names",
        more_hints=[
          f'Reserved VRF names are {r_list}',
          'Set defaults.vrf.attributes.reserved attribute to change that list' ],
        category=log.IncorrectValue,
        module='vrf')

    if 'loopback' in vdata:
      validate_vrf_loopback(vname,vdata,obj,topology)

    if 'rd' in vdata:
      if vdata.rd is None:      # RD set to None can be used to auto-generate RD while preventing RD inheritance
        continue                # ... skip the rest of the checks
      if isinstance(vdata.rd,int):
        asn = asn or get_rd_as_number(obj,topology)
        if not asn:
          log.error(f'VRF {vname} in {obj_name} uses integer RD value without a usable vrf.as or bgp.as AS number',
            log.MissingValue,
            'vrf')
          return
        vdata.rd = f'{asn}:{vdata.rd}'
      else:                     # We know that RD attribute makes some sense (due to type validation), so it's either int or str
        if parse_rdrt_value(vdata.rd) is None:
          log.error(f'RD value in VRF {vname} in {obj_name} ({vdata.rd}) is not in N:N format',
            log.IncorrectValue,
            'vrf')

def normalize_vrf_ids(topology: Box) -> None:
  normalize_vrf_dict(topology,topology)

  for n in topology.nodes.values():
    normalize_vrf_dict(n,topology)

def vrf_needs_id(vrf: Box) -> bool:
  if 'rd' in vrf and 'id' in vrf:
    return False
  return True

def set_vrf_auto_id(vrf: Box, value: typing.Tuple[int,str]) -> None:
  if not 'id' in vrf:
    vrf.id = value[0]

  if not 'rd' in vrf:
    vrf.rd = value[1]

#
# Get VRF RD value needed for import/export values. 
#
# WARNING: Global value takes precedence over node value because you might want to change per-node RD
# values for weird topologies like hub-and-spoke
#
def get_vrf_id(vname: str, obj: Box, topology: Box) -> typing.Optional[str]:
  obj_name = 'global VRFs' if obj is topology else obj.name
  vpath = f'vrfs.{vname}'
  vdata = topology.get(vpath,None) or obj.get(vpath,None)

  if vdata is None:
    log.error(
      f'Cannot get VRF ID for unknown VRF {vname} needed in {obj_name}',
      log.MissingValue,
      'vrf')
    return None

  if not isinstance(vdata,Box):
    log.fatal(f'Internal error: got a VRF definition that is not a dictionary')
    return None

  if not 'rd' in vdata:
    log.fatal(f'Internal error: VRF {vname} in {obj_name} should have a RD value by now')
    return None

  return vdata.rd

#
# Set RD values for all VRFs that have no RD attribute or RD value set to None (= auto-generate)
#
def set_vrf_ids(obj: Box, topology: Box) -> None:
  if not 'vrfs' in obj:
    return

  asn = None
  is_global = obj is topology
  obj_name = 'global VRFs' if obj is topology else obj.name

  for vname,vdata in obj.vrfs.items():                      # Iterate over object VRFs
    if not vrf_needs_id(vdata):                             # Skip if the ID/RD is set
      continue

    if not is_global and vname in topology.get('vrfs',{}):  # Can we copy the global values?
      vdata.id = topology.vrfs[vname].id                    # ... we have to copy individual values because
      vdata.rd = topology.vrfs[vname].rd                    # ... we cannot simply merge global into node data
      continue                                              # ... before post-transform

    asn = asn or get_rd_as_number(obj,topology)
    if not asn:
      log.error(f'Need a usable vrf.as or bgp.as to create auto-generated VRF RD for {vname} in {obj_name}',
        log.MissingValue,
        'vrf')
      return
    set_vrf_auto_id(vdata,get_next_vrf_id(asn))

#
# Set import/export route targets
#
def set_import_export_rt(obj : Box, topology: Box) -> None:
  if not 'vrfs' in obj:
    return None

  is_global = obj is topology
  obj_id   = 'vrfs' if obj is topology else f'nodes.{obj.name}.vrfs'
  asn      = None

  for vname,vdata in obj.vrfs.items():
    for rtname in ['import','export']:
      if not rtname in vdata:
        if not is_global and vname in topology.get('vrfs',{}):        # Copy global RT into node RT if available
          vdata[rtname] = topology.vrfs[vname][rtname]                # ... see set_vrf_ids for detailed description
          continue                                                    # ... of this hack

        vdata[rtname] = [ vdata.rd ]                                  # No usable parent RT, set RT to RD
        continue

      must_be_list(vdata,rtname,f'{obj_id}.{vname}')

      rtlist = []     # The final parsed and looked-up list of RT values
      for rtvalue in vdata[rtname]:
        if isinstance(rtvalue,int):         # RT can be specified as an integer, in which case ASN is prepended to it
          asn = asn or get_rd_as_number(obj,topology)
          if not asn:
            log.error(f'VRF {vname} in {obj_id} uses integer {rtname} value without a usable vrf.as or bgp.as AS number',
              log.MissingValue,
              'vrf')
            continue
          rtvalue = f'{asn}:{rtvalue}'
        elif not isinstance(rtvalue,str):   # If RT is not an integer, it really should be a string
          log.error(f'{rtname} value {rtvalue} in VRF {vname} in {obj_id} should be a string or an integer',
            log.IncorrectValue,
            'vrf')
          continue
        else:
          if ':' in rtvalue:                # If there's a colon in RT value, then we're assuming N:N format
            if parse_rdrt_value(rtvalue) is None:
              log.error(f'{rtname} value {rtvalue} in VRF {vname} in {obj_id} is not in valid N:N format',
                log.IncorrectValue,
                'vrf')
              continue
          else:                             # Otherwise the RT value should refer to another VRF name
            rtvalue = get_vrf_id(rtvalue,obj,topology)
            if rtvalue is None:
              continue            # Error message generated in get_vrf_id

        rtlist.append(rtvalue)

      vdata[rtname] = rtlist

#
# VRF route leaking is usually implemented through BGP VPNv4 address families
# Check whether we have BGP AS configured on all nodes that use VRFs with route leaking
# (identified as import or export RT not equal to [ RD ])
#

def validate_vrf_route_leaking(node : Box) -> None:
  for vname,vdata in node.vrfs.items():
    simple_rt = [ vdata.rd ]
    leaked_routes = vdata['import'] and vdata['import'] != simple_rt
    leaked_routes = leaked_routes or (vdata['export'] and vdata['export'] != simple_rt)
    if leaked_routes:
      vdata._leaked_routes = True
      if not node.get('bgp.as',None):
        if node.get('vrf.as',None):
          node.bgp['as'] = node.vrf['as']
        else:
          log.error(
            f"VRF {vname} on {node.name} uses inter-VRF route leaking, but there's no BGP AS configured on the node",
            log.MissingValue,
            'vrf')

# If we have an in-VRF loopback, fix parent interface for VRF IPv4 unnumbered interfaces
#
def fix_vrf_unnumbered(node: Box, vrfname: str, lbdata: Box) -> None:
  for intf in node.get('interfaces',[]):
    if 'vrf' not in intf or intf.vrf != vrfname:                # Skip irrelevant interfaces
      continue
    if intf.get('ipv4',None) is not True:                       # Skip interfaces that are not unnumbered
      continue

    intf._parent_intf = lbdata.ifname                           # Make in-VRF loopback the parent interface for
    intf._parent_ipv4 = lbdata.ipv4                             # ... in-VRF IPv4 unnumbereds
    intf._parent_vrf  = vrfname                                 # ... and remember where the data came from

def vrf_loopbacks(node : Box, topology: Box) -> None:
  loopback_name = devices.get_device_attribute(node,'loopback_interface_name',topology.defaults)
  loopback_global_attr = list(topology.defaults.attributes.loopback)

  if not loopback_name:                                                        # pragma: no cover -- hope we got device settings right ;)
    log.print_verbose(f'Device {node.device} used by {node.name} does not support VRF loopback interfaces - skipping assignment.')
    return

  node_vrf_loopback = get_effective_module_attribute(
                        path = 'vrf.loopback',
                        node = node,
                        topology = topology)
  for vrfname,v in node.vrfs.items():
    vrf_loopback = v.get('loopback',None) or node_vrf_loopback        # Do we have VRF loopbacks enabled in the node or in the VRF?
    if not vrf_loopback:                                              # ... nope, move on
      continue

    # Note: set interface ifindex to v.vrfidx if you want to have VRF-numbered loopbacks
    #
    ifdata = get_box({                                                # Create interface data structure
      'type': "loopback",
      'name': f'VRF Loopback {vrfname}',
      'neighbors': [],
      'vrf': vrfname,})

    links.create_virtual_interface(node,ifdata,topology.defaults)     # Use common function to create loopback interface

    lb_path = f'nodes.{node.name}.vrfs.{vrfname}.loopback'
    lb_pool: typing.Optional[str] = 'vrf_loopback'
    if isinstance(vrf_loopback,Box):
      ifdata += { k:v for k,v in vrf_loopback.items() if k not in loopback_global_attr }
      if 'ipv4' in vrf_loopback or 'ipv6' in vrf_loopback:
        vrfaddr = addressing.parse_prefix(vrf_loopback,path=lb_path)
        lb_pool = None
      elif 'pool' in vrf_loopback:
        lb_pool = vrf_loopback.pool
    if lb_pool:
      vrfaddr = addressing.get(topology.pools, [ lb_pool ])

    if not vrfaddr:
      continue

    if 'ospf' in node.get('module',[]) and 'ospf.area' not in ifdata:
      ospf_area = get_effective_module_attribute(
                    path = 'ospf.area',
                    link = v,
                    node = node,
                    topology = topology)
      ifdata.ospf.area = ospf_area

    for af in vrfaddr:
      if vrfaddr[af].prefixlen != vrfaddr[af].max_prefixlen:
        ifdata[af] = addressing.get_nth_ip_from_prefix(vrfaddr[af],1)
      else:
        ifdata[af] = str(vrfaddr[af])
      vrfaddr[af] = str(ifdata[af])                                         # Save string copy in vrfaddr, we need it later
      node.vrfs[vrfname].af[af] = True                                      # Enable the af if not already

    if 'ipv4' in ifdata:                                                    # Can we use VRF loopback for in-VRF unnumbereds?
      fix_vrf_unnumbered(node,vrfname,ifdata)

    if not 'networks' in v:                                                 # List of networks to advertise in VRF BGP instance
      v.networks = []

    v.networks.append(vrfaddr)
    node.interfaces.append(ifdata)

    # add loopback addresses to the vrf data as well
    v.loopback_address = vrfaddr

  return

"""
get_vrf_loopback: Given a node and a VRF name, get a loopback interface from that VRF
"""
def get_vrf_loopback(node: Box, vrf: str) -> typing.Optional[Box]:
  for intf in node.interfaces:                    # Loop over all interfaces
    if intf.type != 'loopback':                   # Not a loopback interface? Move on...
      continue
    if intf.get('vrf',None) != vrf:               # Not in the correct VRF? Move on
      continue

    return intf                                   # Found the VRF loopback, return it.
  
  return None                                     # Otherwise, return "not found"

"""
create_vrf_links -- create VRF links based on VRF 'links' attribute

* Iterate over global VRFs
* If a VRF has 'links' attribute, verify that it's a list
* Iterate over the 'links' list
* Normalize every link in the list, add 'vrf: vname' attribute and append the link
  to global list of links
"""

def create_vrf_links(topology: Box) -> None:
  if not 'vrfs' in topology:                                                # No global VRFs, nothing to do
    return

  for vname,vdata in topology.vrfs.items():                                 # Iterate over global VRFs
    if not isinstance(vdata,Box):                                           # VRF not yet a dictionary?
      continue                                                              # ... no problem, skip it
    if not 'links' in vdata:                                                # No VRF links?
      continue                                                              # ... no problem, move on

    for cnt,l in enumerate(vdata.links):                                    # So far so good, now iterate over the links
      link_data = links.adjust_link_object(                                 # Create link data from link definition
                    l=l,
                    linkname=f'vrfs.{vname}.links[{cnt+1}]',
                    nodes=topology.nodes)
      if link_data is None:
        continue
      link_data.vrf = vname                                                 # ... add VRF
      link_data.linkindex = links.get_next_linkindex(topology)              # ... add linkindex (we're late in the process)
      topology.links.append(link_data)                                      # ... and append new link to global link list

    vdata.pop('links')                                                      # Finally, clean up the VLAN definition

class VRF(_Module):

  # Note: validation of 'vrfs' dictionary has already been done during top-level element validation
  def module_pre_transform(self, topology: Box) -> None:

    if 'groups' in topology:
      groups.export_group_node_data(topology,'vrfs','vrf',copy_keys=['rd','export','import'])

    init_vrf_static_ids(topology)

    normalize_vrf_ids(topology)                         # Normalize global and node vrfs, if any
    if not 'vrfs' in topology:                          # No global VRFs, nothing to do
      return

    create_vrf_links(topology)                          # Create VRF links (and remove 'links' attribute)
    log.exit_on_error()
    populate_vrf_static_ids(topology)
    set_vrf_ids(topology,topology)
    set_import_export_rt(topology,topology)

  # Note: validation of 'nodes.x.vrfs' dictionary has already been done during node validation
  def node_pre_transform(self, node: Box, topology: Box) -> None:
    # Check if any global vrfs need to be pulled in due to being referenced by a vlan
    vlan_vrfs = [ vdata.vrf for vname,vdata in node.get('vlans',{}).items() if 'vrf' in vdata ]
    if not 'vrfs' in node:
      if not vlan_vrfs:  # No local vrfs and no vlan references -> exit
        return
      node.vrfs = {}     # Prepare to pull in global vrfs

    for vname in set(list(node.vrfs.keys()) + vlan_vrfs):  # Filter out duplicates
      if node.vrfs[vname] is None:                         # Make sure the VRF dictionary exists
        node.vrfs[vname] = {}

    set_vrf_ids(node,topology)
    set_import_export_rt(node,topology)

  def link_pre_transform(self, link: Box, topology: Box) -> None:
    pass

  #
  # The post-link-transform hook must normalize VRF data and pull global VRF data into
  # nodes so we can use the node VRF data in copy_node_data_into_interfaces module function
  #
  # We have to iterate over all VRF interfaces, validate VRF names (which was previously done
  # in post-transform hook), and populate node VRF data (moved from post-transform hook)
  #
  def node_post_link_transform(self, node: Box, topology: Box) -> None:
    for ifdata in node.interfaces:
      if not 'vrf' in ifdata:                                           # Check only VRF interfaces
        continue

      vrf_data_path = f'vrfs.{ifdata.vrf}'
      if not topology.get(vrf_data_path,None) and not node.get(vrf_data_path,None):
        log.error(
          f'VRF {ifdata.vrf} used on an interface in {node.name} is not defined in the node or globally',
          log.MissingValue,
          'vrf')
        continue

      if not ifdata.vrf in node.vrfs:                                   # Local VRF not present, mark as required
        node.vrfs[ifdata.vrf] = {}

    if not 'vrfs' in node:
      return

    for vname in node.vrfs.keys():
      if vname in topology.get('vrfs',{}):                              # Carefully check for global VRF
        node.vrfs[vname] = topology.vrfs[vname] + node.vrfs[vname]      # ... and do the data merge

    # Set additional loopbacks (one for each defined VRF)
    vrf_loopbacks(node, topology)

  def node_post_transform(self, node: Box, topology: Box) -> None:
    vrf_count = 0

    for ifdata in node.interfaces:
      if 'vrf' in ifdata:
        vrf_count += 1
        if not node.vrfs[ifdata.vrf].rd:
          log.error(
            f'VRF {ifdata.vrf} used on an interface in {node.name} does not have a usable RD',
            log.MissingValue,
            'vrf')
          continue

        for af in ['v4','v6']:
          if f'ip{af}' in ifdata:
            node.af[f'vpn{af}'] = True
            node.vrfs[ifdata.vrf].af[f'ip{af}'] = True

    vrf_lb = node.get('vrf.loopback',False)
    for vdata in node.get('vrfs',{}).values():
      if 'loopback' in vdata or vrf_lb:
        vrf_count += 1

    if log.debug_active('vrf'):
      print( f"vrf node_post_transform on {node.name}: counted {vrf_count} VRFs on interfaces/loopbacks" )
    features = devices.get_device_features(node,topology.defaults)

    # Do we have any need for the VRF module?
    if not vrf_count:
      log.warning(
        text=f"Node {node.name} uses no VRFs, removing 'vrf' from node modules",
        module='vrf',
        flag='inactive',
        hint='inactive')

      # Remove VRF module from the node if the node has no VRFs, unless the vrf.keep_module flag is set
      if not features.get('vrf.keep_module',False):
        remove_module(node,'vrf',['vrfs'])
      
      return

    node.vrfs = node.vrfs or {}     # ... otherwise make sure the 'vrfs' dictionary is not empty
    vrfidx = 100

    # Check that all VRFs have a well-defined data structure (should be at this point, unless someone used groups.node_data)
    for k,v in node.vrfs.items():
      if v is None or not 'id' in v:
        log.error(
          f"Found invalid VRF {k} on node {node.name}. Did you mention it only in groups.node_data? You can't do that.",
          log.IncorrectValue,
          'vrf')
        log.exit_on_error()

    # We need unique VRF index to create OSPF processes, assign in order sorted by VRF ID "for consistency"
    for v in sorted(node.vrfs.values(),key=lambda v: v.id):
      v.vrfidx = vrfidx
      vrfidx = vrfidx + 1

    validate_vrf_route_leaking(node)

    # Finally, set BGP router ID if we set BGP AS number
    #
    if node.get('bgp.as',None) and not node.get('bgp.router_id',None):
      _routing.router_id(node,'bgp',topology.pools)
      _routing.process_imports(node,'bgp',topology,global_vars.get_const('vrf_igp_protocols',['connected']))
