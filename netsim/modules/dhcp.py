#
# DHCP module
#
import typing
from box import Box
import netaddr

from . import _Module,get_effective_module_attribute
from ..utils import log, strings
from .. import data
from ..augment.nodes import reserve_id
from ..augment import devices
from ..data.validate import validate_attributes,must_be_string

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
    if not intf.get('dhcp.client',False):
      continue
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

      if not intf.get('dhcp.vrf',False):
        continue
      if not features.dhcp.vrf:
        log.error(
          f'Node {node.name} (device {node.device}) cannot perform inter-VRF DHCP relaying',
          category=log.IncorrectValue,
          module='dhcp')
        OK = False

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
  topology.dhcp.pools = []

  for link in topology.get('links',[]):                     # Iterate over lab topology links
    if not link.get('dhcp.subnet'):                         # dhcp.subnet is set if there's at least one DHCP client on the link
      continue

    subnet = data.get_empty_box()                           # Create a DHCP pool data structure

    for af in ('ipv4','ipv6'):                              # Iterate over link address families
      if af not in link.dhcp.subnet or af not in link.prefix:
        continue                                            # No AF prefix or no clients within this AF

      subnet[af] = link.prefix[af]                          # Copy link prefix into the pool
      subnet.name = link.get('name','') or link.get('_linkname','')
      subnet.clean_name = strings.make_id(subnet.name)      # Get pool name from link and clean it up

      if af in link.get('gateway',{}):                      # Save default gateway if present
        subnet.gateway[af] = link.gateway[af]

      for intf in link.get('interfaces',[]):                # Now iterate over the interfaces attached to the link
        if af not in intf or af in intf.get('dhcp.client',{}):
          continue                                          # Ignore IP addresses of DHCP clients

        if af not in subnet.excluded:                       # Create the excluded list if needed
          subnet.excluded[af] = []

        addr = str(netaddr.IPNetwork(intf[af]).ip)          # Transform interface CIDR address into pure address
        subnet.excluded[af].append(addr)                    # ... and append it to the excluded addresses

    topology.dhcp.pools.append(subnet)                      # Append the new pool to the list of pools

'''
Set the dhcp.pools list in the DHCP server node data
'''
def set_dhcp_server_pools(node: Box, topology: Box) -> None:
  if not node.get('dhcp.server',False):                     # Node is not a DHCP server, get out
    return

  if not topology.get('dhcp.pools',False):                  # Build a topology-wide list of DHCP pools if needed
    build_topology_dhcp_pools(topology)

  node.dhcp.pools = topology.dhcp.pools                     # And copy topology DHCP pools into DHCP server node data

class DHCP(_Module):

  """
  Before going into link transformation, find IPv4 and IPv6 interface addresses set to DHCP,
  remove them, and add DHCP to parent node modules.
  """
  def link_pre_transform(self, link: Box, topology: Box) -> None:
    for intf in link.get('interfaces',[]):
      for af in ('ipv4','ipv6'):
        if intf.get(af,False) != 'dhcp':            # Interface is not using DHCP, move on
          continue

        if not intf.node in topology.nodes:         # Node is not valid. Weird, but move on
          continue

        intf.pop(af)                                # Pop the interface address -- we don't want to confuse link augmentation
        intf.dhcp.client[af] = True                 # Set DHCP client flag on the interface
        link.dhcp.subnet[af] = True                 # ... and 'we have DHCP clients' flag on the subnet

        node = topology.nodes[intf.node]            # Get parent node
        if 'module' not in node:                    # ... and enable DHCP module on the node
          node.module = [ 'dhcp' ]
        elif 'dhcp' not in node.module:
          node.module.append('dhcp')

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

    if node.get('dhcp.server',False):
      set_dhcp_server_pools(node,topology)
