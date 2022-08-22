#
# VXLAN module
#
import typing
from box import Box
import netaddr

from . import _Module,get_effective_module_attribute
from .. import common
from .. import data
from ..data import get_from_box
from ..augment import devices
from .. import addressing

#
# Check VXLAN-enabled VLANs
#
def node_vlan_check(node: Box, topology: Box) -> bool:
  if not node.vxlan.vlans:            # Create a default list of VLANs if needed
    node.vxlan.vlans = [ name for name,value in node.vlans.items() if 'vni' in value ]

  OK = True
  vlan_list = []
  for vname in node.vxlan.vlans:
    #
    # Report error for unknown VLAN names in VLAN list (they are not defined globally or on the node)
    if not vname in node.vlans and not vname in topology.get('vlans',{}):
      common.error(
        f'Unknown VLAN {vname} is specified in the list of VXLAN-enabled VLANs in node {node.name}',
        common.IncorrectValue,
        'vxlan')
      OK = False
      continue
    #
    # Skip VLAN names that are valid but not used on this node
    if not vname in node.vlans:
      continue
    if not 'vni' in node.vlans[vname]:
      common.error(
        f'VXLAN-enabled VLAN {vname} in node {node.name} does not have a VNI',
        common.IncorrectValue,
        'vxlan')
      OK = False
    else:
      vlan_list.append(vname)

  node.vxlan.vlans = vlan_list
  return OK

#
# Set VTEP IPv4/IPv6 address
#
def node_set_vtep(node: Box, topology: Box) -> bool:
  if topology.defaults.vxlan.use_v6_vtep and not 'ipv6' in node.loopback:
    common.error(
      f'You want to use IPv6 VTEP -- VXLAN module needs an IPv6 address on loopback interface of {node.name}',
      common.IncorrectValue,
      'vxlan')
    return False

  if not 'ipv4' in node.loopback and not topology.defaults.vxlan.use_v6_vtep:
    common.error(
      f'VXLAN module needs an IPv4 address on loopback interface of {node.name}',
      common.IncorrectValue,
      'vxlan')
    return False

  vtep_ip = ""
  vtep_af = 'ipv6' if topology.vxlan.use_v6_vtep else 'ipv4'
  vtep_ip = node.loopback[vtep_af]
  node.vxlan.vtep = str(netaddr.IPNetwork(vtep_ip).ip)              # ... and convert IPv4(v6) prefix into an IPv4(v6) address
  return True

#
# Build VLAN-specific VTEP list
#
def build_vtep_list(vlan: Box, node: str, nodes: typing.List[str], topology: Box) -> list:
  vlan.vtep_list = []                                               # Start with an emtpy VTEP list
  for n in nodes:
    if n == node:                                                   # Skip own node
      continue
    ndata = topology.nodes[n]
    if not 'vlans' in ndata:                                        # No VLANs on remote node, skip it
      continue
    vni_match = filter(lambda x: x.vni == vlan.vni,ndata.vlans.values())
    if list(vni_match):                                             # Is there a VLAN with matching VNI on remote node?
      vlan.vtep_list.append(ndata.vxlan.vtep)                       # ... if so, add remote VTEP to VLAN flood list

  return_value = vlan.vtep_list                                     # We'll return whatever we built
  if not vlan.vtep_list:                                            # ... but will remove empty VTEP list from VLAN data
    vlan.pop('vtep_list')

  return return_value

class VXLAN(_Module):

  def node_pre_transform(self, node: Box, topology: Box) -> None:
    flooding_values = ['static']
    for m in ['evpn']:
      if m in node.module:
        flooding_values.append(m)

    data.must_be_string(
      parent = node.vxlan,
      key = 'flooding',
      path = f'nodes.{node.name}.vxlan',
      valid_values = flooding_values)

  # We need multi-step post-transform node handling, so we have to do that in
  # module_post_transform
  #
  def module_post_transform(self, topology: Box) -> None:
    vxlan_domain_list: typing.Dict[str,list] = {}

    if not 'use_v6_vtep' in topology.vxlan:                         # Copy IPv6 VTEP setting into global parameter
      topology.vxlan.use_v6_vtep = topology.defaults.vxlan.use_v6_vtep

    for name,ndata in topology.nodes.items():
      if not 'vxlan' in ndata.get('module',[]):                     # Skip nodes without VXLAN module
        continue
      if not 'vlans' in ndata:                                      # Skip VXLAN-enabled nodes without VLANs
        continue

      if not node_vlan_check(ndata,topology):                       # Check VLANs
        continue
      if not node_set_vtep(ndata,topology):                         # Set VTEP IP address
        continue

      vxlan_domain = ndata.vxlan.domain                             # Find VXLAN flooding domain name
      if not vxlan_domain in vxlan_domain_list:                     # Unknown VXLAN domain, prepare an empty list
        vxlan_domain_list[vxlan_domain] = []
      vxlan_domain_list[vxlan_domain].append(name)                  # Add current node to VXLAN domain list

    for domain,nodes in vxlan_domain_list.items():                  # Iterate over VXLAN flooding domains
      for node in nodes:                                            # ... and over all nodes in each domain
        ndata = topology.nodes[node]
        if ndata.vxlan.get('flooding') != 'static':                 # Skip nodes that are not using static replication lists
          continue

        vtep_set = set()
        for vlan in ndata.vlans.values():                           # Iterate over all VLANs defined in current node
          if 'vni' in vlan:                                         # Are we dealing with VXLAN-enabled VLAN?
            vtep_list = build_vtep_list(vlan,node,nodes,topology)   # Build VLAN-specific VTEP list
            vtep_set.update(vtep_list)                              # ... and add it to node-level VTEP set


        ndata.vxlan.vtep_list = sorted(list(vtep_set))              # Convert node-level VTEP set into a list
