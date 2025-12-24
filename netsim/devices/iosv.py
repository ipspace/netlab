#
# Cisco IOSv quirks
#
import typing

from box import Box

from ..modules import _routing
from ..utils import log
from . import _Quirks, report_quirk


# Cisco IOSv does not support VRRP on BVI interfaces. Go figure...
#
def check_vrrp_bvi(node: Box, topology: Box) -> None:
  for intf in node.interfaces:
    if intf.get('gateway.protocol',None) != 'vrrp':                     # No VRRP, move on
      continue

    if intf.get('type',None) != 'svi':                                  # Not a BVI interface, move on
      continue

    report_quirk(
      text=f'Cisco IOSv cannot run VRRP on BVI interfaces.',
      node=node,
      category=log.IncorrectType,
      quirk='vrrp_bvi')
    return

'''
IOS does not support passive interfaces with RIPng
'''
def check_ripng_passive(node: Box, topology: Box) -> None:
  for intf in _routing.routing_protocol_interfaces(node,'ripv2'):
    if 'ipv6' in intf and intf.get('ripv2.passive',False):
      report_quirk(
        f'Cisco IOS/IOS-XE does not support passive RIPng interfaces - node {node.name} intf {intf.ifname}({intf.name})',
        node,
        quirk='ripng.passive',
        category=Warning)

'''
IOSv (classic) does not implement VLAN 1 in a trunk correctly
'''
def vlan_1_subinterface(node: Box, topology: Box) -> None:
  for intf in node.interfaces:
    if intf.type != 'vlan_member' or intf.get('vlan.access_id',None) != 1:
      continue
    report_quirk(
      f'Cisco IOS fails to configure VLAN 1 in a trunk ' +\
      f'(node {node.name} {intf.ifname})',
      node,
      quirk='vlan.trunk_1',
      category=log.IncorrectValue)

ANSIBLE_USE_PARAMIKO: typing.Optional[bool] = None

def use_paramiko(node: Box, topology: Box) -> None:
  global ANSIBLE_USE_PARAMIKO
  if ANSIBLE_USE_PARAMIKO is None:
    try:
      import pylibsshext  # type: ignore
      ANSIBLE_USE_PARAMIKO = pylibsshext.__version__ >= '1.3.0'
    except:
      ANSIBLE_USE_PARAMIKO = False

  if ANSIBLE_USE_PARAMIKO:
    device = node.device
    dev_vars = topology.defaults.devices[device].group_vars
    if 'ansible_network_cli_ssh_type' not in dev_vars:
      dev_vars.ansible_network_cli_ssh_type = 'paramiko'    # Force Paramiko connection
      report_quirk(
        f"Changing Ansible network_cli connection SSH type to 'paramiko'",
        node,
        quirk='paramiko',
        category=Warning,
        more_hints=[ 'The installed version of ansible-pylibssh might not work with Cisco IOS devices' ])

def common_ios_quirks(node: Box, topology: Box) -> None:
  mods = node.get('module',[])
  if 'ospf' in mods:
    _routing.get_unique_router_ids(node,'ospf',topology)

  if 'ripv2' in mods:
    check_ripng_passive(node,topology)

  use_paramiko(node,topology)

class IOS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    if 'gateway' in mods:
      check_vrrp_bvi(node,topology)
    if 'vlan' in mods:
      vlan_1_subinterface(node,topology)

    common_ios_quirks(node,topology)
