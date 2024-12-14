#
# Juniper JunOS quirks
# # Every interface is a subunit ->
# # rename interface names from ge-0/0/0 to ge-0/0/0.0 (and so avoid using unit 0 on the initial template)
# # the same can apply to loopbacks, irbs, ...
# # + if the vlan module is in use, and multiple units are present, set the unit 0 as untagged vlan but with the vlan-id (default 1)
#
from box import Box

from . import _Quirks
from ..utils import log
from ..augment import devices

def unit_0_trick(intf: Box, round: str ='global') -> None:
  oldname = intf.ifname
  newname = oldname + ".0"
  if log.debug_active('quirks'):
    print(" - [{}] Found interface {}, renaming to {}".format(round, intf.ifname, newname))
  intf.ifname = newname
  intf.junos_interface = oldname
  intf.junos_unit = '0'

def fix_unit_0(node: Box, topology: Box) -> None:
  mods = node.get('module',[])
  # Need to understand if I need to configure unit 0 or not.
  base_vlan_interfaces = []

  for intf in node.get('interfaces', []):
    if not '.' in intf.ifname:
        unit_0_trick(intf)
        if 'vlan' in mods:
          # check VLAN params, and add if needed
          if '_vlan_native' in intf:
            # get native ID
            intf._vlan_native_id = node.vlans[intf._vlan_native].id

    if '.' in intf.ifname and intf.ifname != 'irb':
      # get basic interface, and add to list.
      ifname_split = intf.ifname.split('.')
      intf.junos_interface = ifname_split[0]
      intf.junos_unit = ifname_split[1]
      if 'vlan' in mods:
        base_vlan_interfaces.append(ifname_split[0])
  
  # add additional vlan parameters.
  if len(base_vlan_interfaces) > 0:
    for intf in node.get('interfaces', []):
      if intf.junos_unit=='0' and intf.junos_interface in base_vlan_interfaces:
        intf._vlan_master = True
  
  # need to append .0 unit trick to the interface list copied into vrf->ospf
  if 'vrf' in mods and 'ospf' in mods:
    for vname,vdata in node.vrfs.items():
      for intf in vdata.get('ospf', {}).get('interfaces', []):
        if not '.' in intf.ifname:
          unit_0_trick(intf, "vrf({})/ospf".format(vname))

def check_multiple_loopbacks(node: Box, topology: Box) -> None:
  vrf_count: dict = {}
  if 'loopback' in node:
    vrf_count['default'] = 1

  for intf in node.interfaces:
    if intf.get('type','') != 'loopback':
      continue

    vrf = intf.get('vrf','default')
    if vrf in vrf_count:
      vrf_count[vrf] += 1
    else:
      vrf_count[vrf] = 1

  for vname,vcnt in vrf_count.items():
    if vcnt <= 1:
      continue
    log.error(
      f'Node {node.name} (device {node.device}) has {vcnt} loopbacks in vrf {vname}',
      category=log.IncorrectValue,
      module='quirks',
      hint='junos_lb')

class JUNOS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    if log.debug_active('quirks'):
      print("*** DEVICE QUIRKS FOR JUNOS {}".format(node.name))
    fix_unit_0(node,topology)
    check_multiple_loopbacks(node,topology)
