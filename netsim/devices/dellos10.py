#
# Dell OS10 quirks
#
from box import Box, BoxList

from ..utils import routing as _rp_utils
from . import _Quirks, need_ansible_collection, report_quirk


def check_vlan_ospf(node: Box, iflist: BoxList, vname: str) -> None:
  name = node.name
  err_data = []
  for intf in iflist:
    if 'ospf' not in intf or intf.type != 'svi':              # ospf.interfaces is not renamed
      continue
    if 'vlan' in intf:
      vlan = node.get(f"vlans.{intf.vlan.name}",{})
      if 'vni' not in vlan:
        continue                                              # Skip non-VXLAN interfaces
    err_data.append(f'Interface {intf.ifname} VNI {vlan.vni} VRF {vname}')

  if err_data:
    report_quirk(
      f'node {name} cannot run OSPF on virtual-network (SVI) interfaces',
      quirk='svi_ospf',
      more_data=err_data,
      node=node)

"""
check_ospf_originate_default - Check if the topology is using custom 'cost' or 'type' attributes for originated
                               OSPF default routes, if so warn about lack of support
"""
def check_ospf_originate_default(node: Box) -> None:
  ospf_default = node.get('ospf.default',{})
  unsupported_atts = ospf_default.keys() - set(['always'])
  if unsupported_atts:
    report_quirk( f'node {node.name} uses unsupported ospf.default originate attributes that will be ignored',
      quirk='ospf_default_unsupported_attributes',
      category=Warning,
      more_data=sorted(unsupported_atts),
      node=node)

"""
check_anycast_gateways - check that anycast gateways are only used on SVI interfaces, not p2p links

See https://infohub.delltechnologies.com/en-us/l/dell-emc-smartfabric-os10-virtual-link-trunking-reference-architecture-guide-1/ip-anycast-gateway-support-2/
"The Anycast IP-based Layer 3 gateway solution is a lightweight gateway router redundancy protocol that is enabled only on VLANs"

Note: Anycast also requires VLT configuration on the switch, which Netlab can support through the lag module

"""
def check_anycast_gateways(node: Box) -> None:
  err_data = []
  for intf in node.interfaces:
    if intf.type != 'svi' and intf.get('gateway.anycast',None):
      err_data.append(f'Interface {intf.ifname}')
  
  if err_data:
    report_quirk(
      f'Dell OS10 (node {node.name}) does not support anycast on non-SVI interfaces',
      quirk='non_svi_anycast',
      more_data=err_data,
      node=node)

"""
check_vrrp - check if VRRP protocol is requested, not supported on virtual network interfaces
"""
def check_vrrp_on_virtual_networks(node:Box, topology: Box) -> None:
  err_data = []
  for intf in node.interfaces:
    if intf.type == 'svi' and 'virtual-network' in intf.ifname and intf.get('gateway.vrrp',None):
      err_data.append(f'SVI interface {intf.ifname}')

  if err_data:
    report_quirk(
      f'Dell OS10 (node {node.name}) does not support VRRP on virtual networks (used for VXLAN VLANs)',
      quirk='vrrp_on_virtual_networks',
      more_data=err_data,
      node=node)

"""
check_expanded_communities - Check for unsupported 'expanded' communities or regex
"""
def check_expanded_communities(node:Box, topology: Box) -> None:
  for c_name,c_value in node.get('routing.community',{}).items():
    if c_value.get('type',None) != 'standard':
      report_quirk(
        f"Dell OS10 (node {node.name}) does not support communities of type '{c_value.type}'",
        quirk='non-standard_communities',
        node=node)

def check_nssa_area_limitations(node: Box) -> None:
  for (odata,_,_) in _rp_utils.rp_data(node,'ospf'):
    if 'areas' not in odata:
      continue
    for area in odata.areas:
      if area.kind != 'nssa':
        continue
      if 'ipv6' in odata.af:
        report_quirk(
          f'{node.name} cannot configure NSSA type areas for OSPFv3 (area {area.area})',
          more_hints = [ 'Dell OS10 does not support NSSA for OSPFv3' ],
          node=node,
          quirk='ospfv3_nssa')

"""
Update the names of SVI interfaces to use 'virtual-network' instead of 'vlan' when a VNI is assigned
"""
def update_vxlan_svi_names(node:Box, topology: Box) -> None:
  for intf in node.interfaces:
    if intf.type != 'svi': 
      continue
    vlan = topology.vlans[ intf.vlan.name ]
    if 'vni' in vlan:
      new_ifname = intf.ifname.replace('vlan','virtual-network')
      for n in intf.neighbors:                        # Also update ifname in neighbor lists
        nb = topology.nodes[ n.node ]
        for nb_if in nb.interfaces:
          for n2 in nb_if.neighbors:
            if n2.node==node.name and n2.ifname==intf.ifname:
              n2.ifname = new_ifname
      intf.ifname = new_ifname

class OS10(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])

    if 'vxlan' in mods:
      update_vxlan_svi_names(node,topology)           # Use virtual-network for VXLAN VLANs (with 'vni')
      if 'ospf' in mods:                              # OSPF not supported on virtual-network interfaces
        check_vlan_ospf(node,node.interfaces,'default')
        for vname,vdata in node.get('vrfs',{}).items():
          check_vlan_ospf(node,vdata.get('ospf.interfaces',[]),vname)
      if 'gateway' in mods and 'vrrp' in node.get('gateway',{}):
        check_vrrp_on_virtual_networks(node,topology) # Neither is VRRP

    if 'ospf' in mods:
      check_ospf_originate_default(node)
      check_nssa_area_limitations(node)

    if 'gateway' in mods:
      if 'anycast' in node.get('gateway',{}):
        check_anycast_gateways(node)
    if 'routing' in mods:
      check_expanded_communities(node,topology)

  def check_config_sw(self, node: Box, topology: Box) -> None:
    need_ansible_collection(node,'dellemc.os10')
