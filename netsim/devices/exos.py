from box import Box

from ..utils import log
from . import _common, _Quirks, need_ansible_collection, report_quirk

EXOS_VLAN_1_NAME = 'Default'
EXOS_RESERVED_NAMES = ["aaa", "access-list", "account", "accounts", "acl", "auto-peering", "auto-provision", "avb", "bandwidth", "banner", "bfd", "bgp", "bootprelay", "bootrom", "brm", "bvlan", "cdp", "cfgmgr", "cfm", "checkpoint- data", "clear", "clear-flow", "cli", "clipaging", "configuration", "configure", "cos-index", "counters", "cp", "cpu-monitoring", "create", "cvlan", "dcbx", "delete", "devmgr", "dhcp", "dhcp-client", "dhcp-server", "dhcpv6", "diagnostics", "diffserv", "disable", "dns", "dns-client", "dos-protect", "dot1ag", "dot1p", "dot1q", "ds", "dwdm", "eaps", "edp", "elrp", "elrp-client", "elsm", "ems", "enable", "epm", "erps", "esrp", "ethernet", "evpn", "exit", "exsh-var", "fabric", "failsafe- account", "fdb", "firmware", "flow-redirect", "force_synchronize", "forwarding", "get", "gptp", "hal", "hclag", "icmp", "identity- management", "idletimeout", "idmgr", "igmp", "image", "inline-power", "ip", "ip-fix", "ip-mtu", "ip-security", "iparp", "ipconfig", "ipforwarding", "ipmc", "ipmcforwarding", "ipmroute", "iproute", "ipstats", "ipv6", "ipagent", "irdp", "isid", "isis", "jumbo-frame", "jumbo-frame-size", "kernel", "l2pt", "l2stats", "l2vpn", "lacp", "ldap", "learning", "led", "license", "license-info", "licenses", "licMgr", "lldp", "load", "log", "logout", "mac", "mac-binding", "mac-lockdown- timeout", "mac-locking", "macsec", "management", "mcast", "mcm", "mcmgr", "memory", "memorycard", "meter", "mirror", "mlag", "mld", "modify", "mpls", "mrp", "msdp", "msgsrv", "msrp", "mstp", "mv", "mvr", "mvrp", "neighbor- discovery", "netlogin", "nettools", "network-clock", "node", "nodealias", "ntp", "orchestration", "ospf", "ospvdebug", "ospfv3", "otm", "packet", "performance", "pim", "poe", "policy", "ports", "power", "printk", "private-vlan", "process", "protocol", "put", "pwmib", "q", "qosprofile", "qosscheduler", "quit", "radius", "radius- accounting", "refresh", "rip", "ripng", "rmon", "router- discovery", "rtmgr", "run", "safe-default- script", "save", "screen", "script", "security", "session", "set", "sflow", "sharing", "show", "slot", "slot-poll- interval", "slpp", "snmp", "snmpMaster", "snmpv3", "sntp-client", "source", "ssh2", "sshd2", "ssl", "stacking", "stacking- support", "stm", "stp", "stpd", "svlan", "switch", "sys-health-check", "syslog", "sys-recovery- level", "system", "tacacs", "tech-support", "telnet", "telnetd", "tftpd", "throw", "thttpd", "time", "trusted-servers", "tunnel", "twamp", "udp-echo-server", "udp-profile", "unconfigure", "update", "upload", "upm", "usleep", "validate", "var", "version", "vid", "virtual-network", "virtual-router", "vlan", "vm", "vm-tracking", "vman", "vpex", "vr", "vrrp", "vsm", "watchdog", "web", "wred", "wredprofile", "xml-mode", "xml-notification", "xml-test", "xmlc", "xmld", "xx_force_synchronize", "xx_synchronize", "xx_synchronize2"]
# the list of reserved names above is available in the EXOS documentation:
# https://documentation.extremenetworks.com/exos_32.7.1/GUID-F9E4E9B8-4D90-4DCB-B325-87347F797C7B.shtml

def check_reserved_vlans(node: Box, topology: Box) -> None:
  for vname in node.get('vlans',{}).keys():
    if vname in EXOS_RESERVED_NAMES:
      report_quirk(
        text=f'Cannot use VLAN NAME {vname} (VLAN {vname}) on Extreme EXOS',
        node=node,
        category=log.IncorrectValue,
        quirk='vlan.reserved',
        module='quirks')

def check_vrrp_address_families(node: Box) -> None:
  for intf in node.interfaces:
    if intf.get('gateway.protocol',None) != 'vrrp':
      continue

    if 'ipv4' in intf.gateway and 'ipv6' in intf.gateway:
      report_quirk(
        text=f'Extreme EXOS cannot configure IPv4 and IPv6 virtual addresses in the same VRRP instance ({node.name} {intf.ifname})',
        node=node,
        quirk='vrrp_mixed_af',
        category=log.IncorrectType)
      return

def rename_interface_vlan_references(intf: Box, old_name: str, new_name: str) -> None:
  for kw in ('vlan.access','vlan.native','vlan.name','vlan_name','_vlan_native'):
    if intf.get(kw,None) == old_name:
      intf[kw] = new_name

  trunk = intf.get('vlan.trunk',None)
  if trunk and old_name in trunk:
    trunk[new_name] = trunk.pop(old_name)

def default_vlan_1(node: Box) -> None:
  if 'vlans' not in node:
    return

  if EXOS_VLAN_1_NAME in node.vlans and node.vlans[EXOS_VLAN_1_NAME].id != 1:
    report_quirk(
      text=f'{EXOS_VLAN_1_NAME} VLAN must have VLAN tag 1',
      node=node,
      category=log.IncorrectValue)
    return

  vlan_1_name = next(
    (vname for vname,vdata in node.vlans.items() 
       if vdata.get('id',None) == 1 and vname != EXOS_VLAN_1_NAME),
    None)
  if not vlan_1_name:
    return

  node.vlans[EXOS_VLAN_1_NAME] = node.vlans.pop(vlan_1_name)

  for intf in node.interfaces:
    rename_interface_vlan_references(intf,vlan_1_name,EXOS_VLAN_1_NAME)

  report_quirk(
    text='Extreme EXOS reserves VLAN ID 1 for the built-in Default VLAN',
    more_data=f'Renaming VLAN {vlan_1_name} to {EXOS_VLAN_1_NAME} on node {node.name}',
    node=node,
    quirk='vlan.default_1',
    category=Warning)

class EXOS(_Quirks):

  @classmethod
  def device_quirks(cls, node: Box, topology: Box) -> None:
    if 'vlan' in node.get('module',[]):
      default_vlan_1(node)
      check_reserved_vlans(node,topology)
      _common.check_tagged_vlan_1(node)
    if 'gateway' in node.get('module',[]):
      check_vrrp_address_families(node)

  def check_config_sw(self, node: Box, topology: Box) -> None:
    need_ansible_collection(node,'community.network',version='5.1.0')
