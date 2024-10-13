#
# DHCP module
#
import typing
from box import Box
import netaddr

from . import _Module,_routing
from ..utils import log, strings
from .. import data
from ..augment import devices

'''
Do sanity checks on DHCP data:

* Use device features to check whether the clients and servers are supported on the
  nodes on which they are enabled
* Check DHCP relay support
* Check inter-VRF DHCP relay support
'''
def check_protocol_support(node: Box, topology: Box) -> bool:
  features = devices.get_device_features(node,topology.defaults)
  OK = True

  # Can a device configured as a DHCP server be on?
  #
  if node.get('dhcp.server',False) and not features.dhcp.server:
    log.error(
      f'Node {node.name} (device {node.device}) cannot be a DHCP server',
      category=log.IncorrectValue,
      module='dhcp')
    OK = False

  # Iterate over node interface, check whether the device supports configured
  # DHCP clients
  #
  for intf in node.interfaces:
    if not intf.get('dhcp.client',False):         # Not a DHCP client? OK
      continue
    if intf.get('dhcp.server',False):             # Also a DHCP relay? That can't be
      intf.dhcp.pop('client',None)                # ... remove the client flag
      continue                                    # ... and move on
    for af in ('ipv4','ipv6'):
      if not af in intf.dhcp.client:
        continue        
      if not features.dhcp.client[af]:
        log.error(
          f'Node {node.name} (device {node.device}) does not support {af} DHCP client',
          more_data= [ f'DHCP client is used on interface {intf.ifname} ({intf.name})' ],
          category=log.IncorrectValue,
          module='dhcp')
        OK = False

  # Iterate over configured DHCP relays, check whether the device supports DHCP relaying
  # and inter-VRF DHCP relaying and whether the DHCP servers are legit
  for intf in node.interfaces:
    if not intf.get('dhcp.server',False):
      continue
    if not features.dhcp.relay:
      log.error(
        f'Node {node.name} (device {node.device}) cannot be a DHCP relay',
        category=log.IncorrectValue,
        module='dhcp')
      OK = False

    for srv in intf.dhcp.server:
      if not topology.nodes.get(f'{srv}.dhcp.server',False):
        log.error(
          f'Node {srv} used for DHCP relaying on node {node.name} is not a DHCP server',
          category=log.IncorrectValue,
          module='dhcp')
        OK = False

    node.dhcp.relay = True                                # Remember the node uses a DHCP relay

    if not intf.get('dhcp.vrf',False):                    # Did the user request inter-VRF relaying?
      continue

    if not features.dhcp.vrf:                             # Does the device support inter-VRF relaying?
      log.error(                                          # No, report an error
        f'Node {node.name} (device {node.device}) cannot perform inter-VRF DHCP relaying',
        category=log.IncorrectValue,
        module='dhcp')
      OK = False
    else:                                                 # Inter-VRF relaying is configured
      if node.get('dhcp.vrf',None) is None:               # ... assume the device can insert DHCP VPN option
        node.dhcp.vrf = True                              # ... but only if the dhcp.vrf node value is not set

    # 'global' is a valid VRF keyword for VRF-to-global relaying
    # In all other cases, the VRF has to be present on the node
    #
    vrf = intf.get('dhcp.vrf')
    if vrf == 'global':
      continue

    if vrf not in node.get('vrfs',{}):
      log.error(
        f'VRF {vrf} used for DHCP relaying on node {node.name} has no interfaces on that node',
        category=log.IncorrectValue,
        module='dhcp')
      OK = False

  return OK

'''
We don't want to build DHCP pools in Jinja2 templates. This function:

* Analyzes all links in the lab topology
* Identifies links with DHCP clients
* Transforms each link with DHCP clients into a DHCP pool

Each DHCP pool could have:

* Link name and cleaned-up link name
* IPv4 and IPv6 prefix
* IPv4 first-hop gateway
* Excluded IPv4 and IPv6 addresses
'''

def build_topology_dhcp_pools(topology: Box) -> None:
  pools = data.get_empty_box()

  # Phase 1: Build a list of potential pools from VLANs
  #
  for vname,vdata in topology.get('vlans',{}).items():
    if vdata.get('mode') == 'route':                        # Won't deal with routed VLANs
      continue

    pid = strings.make_id(f'vlan_{vname}')
    for af in log.AF_LIST:
      af_pfx = vdata.get(f'prefix.{af}',None)
      if isinstance(af_pfx,str):
        pools[pid][af] = af_pfx

      if vdata.get(f'gateway.{af}',None):
        pools[pid].gateway[af] = vdata.gateway[af]

    if pid in pools and 'vrf' in vdata:                     # Copy VLAN VRF if we got some usable prefixes
      pools[pid].vrf = vdata.vrf

  # Phase 2: Iterate over node interfaces, find SVIs, and build excluded IP list
  #
  for node,ndata in topology.get('nodes',{}).items():
    for intf in ndata.get('interfaces',[]):
      vname = intf.get('vlan.name')
      if not vname:
        continue
      pid = strings.make_id(f'vlan_{vname}')

      if pid not in pools:
        continue

      # Iterate over all address families, finding true interface addresses,
      # converting them from CIDR format to IPv4/IPv6 address format, and
      # appending them to the pool.excluded.af list
      #
      for af in log.AF_LIST:
        if af in intf and isinstance(intf[af],str):
          data.append_to_list(pools[pid].excluded,af,str(netaddr.IPNetwork(intf[af]).ip))

  for link in topology.get('links',[]):                     # Iterate over lab topology links
    if not link.get('dhcp.subnet'):                         # dhcp.subnet is set if there's at least one DHCP client on the link
      continue

    vname = link.get('vlan.access',None)
    lname = link.get('name','') or link.get('_linkname','')
    if vname:
      pid = strings.make_id(f'vlan_{vname}')
    else:
      pid = strings.make_id(lname)
      pools[pid].name = lname
      if 'vrf' in link:                                     # Copy VRF information from non-VLAN links
        pools[pid].vrf = link.vrf                           # ... to support VRF-aware DHCP servers

    pools[pid].active = True
    for af in log.AF_LIST:                                  # Iterate over link address families
      if af not in link.dhcp.subnet:
        continue                                            # No clients within this AF

      af_pfx = link.get(f'prefix.{af}',None)                # Get AF prefix
      if not isinstance(af_pfx,str):
        continue                                            # No usable AF prefix

      if af in pools[pid]:                                  # Pool already has a prefix
        if pools[pid][af] != af_pfx:                        # Check for mismatch between link and VLAN prefix
          log.error(
            f'Mismatch in DHCP pool {pid} prefix {pools[pid][af]}, link {lname} claims the prefix should be {af_pfx}',
            category=log.IncorrectValue,
            module='dhcp')
      else:
        pools[pid][af] = af_pfx                             # New pool, add prefix

      if af in link.get('gateway',{}):                      # Save default gateway if present
        pools[pid].gateway[af] = str(netaddr.IPNetwork(link.gateway[af]).ip)

      for intf in link.get('interfaces',[]):                # Now iterate over the interfaces attached to the link
        if af not in intf or af in intf.get('dhcp.client',{}):
          continue                                          # Ignore IP addresses of DHCP clients

        # Append non-DHCP addresses to the excluded list
        data.append_to_list(pools[pid].excluded,af,str(netaddr.IPNetwork(intf[af]).ip))        

  topology.dhcp.pools = []                                  # Finally, convert pool data into a list of pools
  for pname,pdata in pools.items():                         # Iterate over collected pools
    if not pdata.active:                                    # We might be dealing with a VLAN that has no
      continue                                              # ... DHCP clients
    pdata.pop('active',None)                                # Found an active DHCP pool, remove the 'active' flag
    if not 'name' in pdata:                                 # VLAN pools might not have a 'name' attribute
      pdata.name = pname
    pdata.clean_name = pname                                # ... set the 'clean_name'
    topology.dhcp.pools.append(pdata)                       # ... and append the new pool to the list of pools

'''
Set the dhcp.pools list in the DHCP server node data
'''
def set_dhcp_server_pools(node: Box, topology: Box) -> None:
  if not node.get('dhcp.server',False):                     # Node is not a DHCP server, get out
    return

  if not topology.get('dhcp.pools',False):                  # Build a topology-wide list of DHCP pools if needed
    build_topology_dhcp_pools(topology)

  node.dhcp.pools = topology.dhcp.pools                     # And copy topology DHCP pools into DHCP server node data
  for p in node.dhcp.pools:                                 # Final step: iterate over the DHCP pools
    if 'vrf' in p:                                          # ... looking for VRF subnets
      if node.get('dhcp.vrf',None) is None:                 # ... and if the node doesn't have 'VRF-aware pools' flag
        node.dhcp.vrf = True                                # ... set it to True

'''
set_dhcp_relay: Convert DHCP server names into IP addresses of DHCPv4/DHCPv6 relays
'''

def set_dhcp_relay(intf: Box, n_name: str, topology: Box) -> None:
  if not intf.get('dhcp.server',False):                     # Relay not configured on the interface, get out
    return

  for af in ('ipv4','ipv6'):                                # We could be relaying IPv4 or IPv6
    #
    # Do we have any DHCP clients attached to this interface?
    clist = [ ngb.node for ngb in intf.neighbors if ngb.get(f'dhcp.client.{af}',False) ]
    if not clist:                                           # Nope, no need to set DHCP relay for this interface
      continue

    intf.dhcp.relay[af] = []                                # Build the list of the relay targets
    for srv_name in intf.get('dhcp.server',[]):             # Iterate over relay target names
      # Get control-plane interface for the relay target
      cp_intf = _routing.get_remote_cp_endpoint(topology.nodes[srv_name])
      if not cp_intf:                                       # no usable CP interafce, get out
        log.error(
          f'DHCP server {srv_name} used by node {n_name} interface {intf.ifname} has no usable interface',
          category=log.MissingValue,
          module='dhcp')
        continue

      if not af in cp_intf:                                 # Target AF not configured on the server CP interface?
        log.error(
          f'Missing {af} address on {cp_intf.ifname} on {srv_name}. Node {n_name} cannot use it as DHCP {af} relay',
          category=log.MissingValue,
          module='dhcp')
        continue

      # We have a usable address on the DHCP server control-plane interface.
      # Add it to the DHCP relay targets
      #
      intf.dhcp.relay[af].append(str(netaddr.IPNetwork(cp_intf[af]).ip))

'''
check_dynamic_routing -- check whether a node uses routing protocols on a DHCP interface
'''

def check_dynamic_routing(intf: Box, node: Box, topology: Box) -> bool:
  if 'bgp' in intf:
    log.error(
      f'You cannot run EBGP over DHCP client interfaces (node {node.name} interface {intf.name})',
      category=log.IncorrectValue,
      module='dhcp')
    intf.pop('bgp',None)
    return False

  OK = True
  for rp in ('ospf','isis'):
    if not rp in intf:
      continue
    features = devices.get_device_features(node,topology.defaults)
    if not features.dhcp.client.routing:
      log.error(
        f'Device {node.device} / node {node.name} cannot run dynamic routing protocols on DHCP client interface',
        more_data = [ f'protocol: {rp}, interface {intf.name}'],
        category=log.IncorrectValue,
        module='dhcp')
      OK = False

  return OK

class DHCP(_Module):

  """
  Before going into link transformation, find IPv4 and IPv6 interface addresses set to DHCP,
  remove them, and add DHCP to parent node modules.
  """
  def link_pre_transform(self, link: Box, topology: Box) -> None:
    for intf in link.get('interfaces',[]):
      for af in ('ipv4','ipv6'):
        if intf.get('dhcp',None):                   # The interface already has DHCP settings, move on
          continue

        # The interface and the link are not using DHCP, move on
        if intf.get(af,False) != 'dhcp' and not link.get(f'dhcp.client.{af}',False):
          continue

        if not intf.node in topology.nodes:         # Node is not valid. Weird, but move on
          continue

        intf.pop(af)                                # Pop the interface address -- we don't want to confuse link augmentation
        intf.dhcp.client[af] = True                 # Set DHCP client flag on the interface
        link.dhcp.subnet[af] = True                 # ... and 'we have DHCP clients' flag on the subnet

        node = topology.nodes[intf.node]            # Get parent node
        data.append_to_list(node,'module','dhcp')   # ... and enable DHCP module on the node

  """
  Final DHCP transformation:

  * Check client/server/relay support
  * Remove static interface addresses on DHCP clients
  * Build DHCP pools on DHCP servers
  """
  def node_post_transform(self, node: Box, topology: Box) -> None:
    if not check_protocol_support(node,topology):
      return

    for intf in node.get('interfaces',[]):
      for af in ('ipv4','ipv6'):
        if intf.get(f'dhcp.client.{af}',False):
          intf.pop(af,None)
          check_dynamic_routing(intf,node,topology)

        if intf.get('dhcp.server',False):
          set_dhcp_relay(intf,node.name,topology)

    if node.get('dhcp.server',False):
      set_dhcp_server_pools(node,topology)
