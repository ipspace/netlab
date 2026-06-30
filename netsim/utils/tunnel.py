#
# Tunnel utilities
#

import ipaddress
import typing

from box import Box

from ..augment import devices as a_devices
from ..augment import links as _links
from ..data import get_box, global_vars
from . import log


def set_tunnel_type(topology: Box) -> None:
  """
  Set 'type: tunnel' on all links with 'tunnel.mode' attribute. Skip this step
  if another tunnel plugin has already done that.
  """
  tunnel_status = global_vars.get('tunnel_status')
  if 'type_set' in tunnel_status:
    return
  
  for link in topology.get('links',[]):
    if not link.get('tunnel.mode',None):
      continue
    if 'type' in link and link.type != 'tunnel':
      log.error(
        f"Link {link._linkname} has tunnel attributes and 'type' set to {link.type}",
        category=log.IncorrectValue,
        module='tunnel')
    else:
      link.type = 'tunnel'

  tunnel_status.type_set = True

def links(topology: Box, tunnel_type: str) -> typing.Generator:
  """
  Return all links with the specified tunnel type
  """
  for link in topology.get('links',[]):
    if link.get('tunnel.mode',None) == tunnel_type:
      yield link

def interfaces(node: Box, tunnel_type: str) -> typing.Generator:
  """
  Return all interfaces with the specified tunnel type
  """
  for intf in node.get('interfaces',[]):
    if intf.get('tunnel.mode',None) == tunnel_type:
      yield intf

def get_tunnel_source(ndata: Box, t_intf: Box, topology: Box) -> typing.Optional[Box]:
  '''
  Find the tunnel source interface using (in descending order) tunnel.type,
  tunnel.vrf, tunnel.link.name and tunnel.link.role. Viable interface(s) are
  also checked for desired transport AF. The first viable interface is returned
  '''
  t_vrf  = t_intf.get('tunnel.vrf',None)
  t_type = t_intf.get('tunnel.source.type',None)
  t_name = t_intf.get('tunnel.source.link.name',None)
  t_role = t_intf.get('tunnel.source.link.role',None)
  t_af   = t_intf.get('tunnel.af','ipv4')

  iflist = ndata.get('interfaces',[])
  if 'loopback' in ndata and t_type == 'loopback' and t_vrf is None:
    iflist += [ ndata.loopback ]

  for intf in iflist:
    if t_type is None:                            # No type means 'not loopback or tunnel'
      if intf.type in ['loopback','tunnel']:      # ... so skip these interfaces
        continue
    elif intf.type != t_type:                     # Otherwise, the type must match (currently, only loopback is allowed)
      continue

    if t_vrf is None:                             # No VRF means 'global routing table'
      if 'vrf' in intf:                           # ... so skip non-global interfaces
        continue
    elif t_vrf != intf.get('vrf',None):           # Otherwise, check the VRF name
      continue

    if t_name and t_name != intf.get('name',None):
      continue                                    # Mismatch in interface name

    if t_role:                                    # Do we want to check on roles?
      if 'role' in intf:                          # Is role specified on the interface?
        if t_role != intf.role:
          continue                                # Mismatch in interface role
      else:                                       # No interface role, let's check link role
        link = _links.get_link_by_index(topology,intf.linkindex)
        if link is None or t_role != link.get('role',None):
          continue                                  # Mismatch in link role

    if t_af not in intf:                          # Is the interface enabled for the desired tunnel transport AF
      continue

    if not isinstance(intf[t_af],str):            # Cannot run tunnels from unnumbered interfaces
      continue

    return get_box({'ifname': intf.ifname, t_af: str(ipaddress.ip_interface(intf[t_af]).ip) })

  return None

def check_feature(
      ndata: Box,
      topology: Box,
      f_name: str,                                # Name of the tunnel feature
      f_desc: str,                                # Description of the tunnel feature (used in error messages)
      f_value: typing.Optional[typing.Union[str,bool]] = None,
      ) -> bool:
  """
  Checks whether the node supports the required tunnel feature
  """
  features = a_devices.get_device_features(ndata,topology.defaults)
  df_value = features.tunnel.get(f_name,None)
  if df_value:
    if f_value is None:
      return True
    
    if isinstance(df_value,list) and f_value in df_value:
      return True
    
    if df_value == f_value:
      return True
  
  log.error(
    f'Device {ndata.device} (node {ndata.name}) does not support {f_desc}',
    log.IncorrectValue,'tunnel')
  return False
