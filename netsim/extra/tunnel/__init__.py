#
# Tunnel utilities
#

import ipaddress
import typing

from box import Box

from ...augment import devices as a_devices
from ...augment import links as _links
from ...data import get_empty_box, global_vars
from ...utils import log


def init(topology: Box) -> typing.NoReturn:
  '''
  Just in case someone has a great idea to use the 'tunnel' plugin, we
  have to set them straight
  '''
  log.fatal("You cannot use the 'tunnel' plugin. Use a plugin for the tunnel mode you're interested in")

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

def get_tunnel_source(ndata: Box, t_intf: Box, topology: Box) -> typing.List[Box]:
  '''
  Find the tunnel source interface using (in descending order) tunnel.type,
  tunnel.vrf, and various tunnel.source parameters. When tunnel.af is set,
  only interfaces enabled for that transport AF are considered; otherwise
  only interfaces with at least one numbered address are included. Returns
  the list of viable interfaces.
  '''
  t_vrf    = t_intf.get('tunnel.vrf',None)
  t_type   = t_intf.get('tunnel.source.type',None)
  t_name   = t_intf.get('tunnel.source.link.name',None)
  t_role   = t_intf.get('tunnel.source.link.role',None)
  t_linkid = t_intf.get('tunnel.source.linkid',None)
  t_af     = t_intf.get('tunnel.af',None)         # Optional transport AF: filter interfaces on it when set

  iflist = ndata.get('interfaces',[])
  if 'loopback' in ndata and t_type == 'loopback' and t_vrf is None:
    iflist = iflist + [ ndata.loopback ]

  underlay_iflist = []

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

    if t_linkid and t_linkid != intf.get('linkid',None):
      continue                                    # Mismatch in link ID

    if t_role:                                    # Do we want to check on roles?
      if 'role' in intf:                          # Is role specified on the interface?
        if t_role != intf.role:
          continue                                # Mismatch in interface role
      else:                                       # No interface role, let's check link role
        link = _links.get_link_by_index(topology,intf.linkindex)
        if link is None or t_role != link.get('role',None):
          continue                                # Mismatch in link role

    if t_af:
      if t_af not in intf:                        # Is the interface enabled for the desired tunnel transport AF
        continue
      if not isinstance(intf[t_af],str):          # Cannot run tunnels from unnumbered interfaces
        continue
    elif not any(af in intf and isinstance(intf[af],str) for af in ('ipv4','ipv6')):
      continue

    underlay_iflist.append(intf)

  if underlay_iflist:                             # Found something?
    return underlay_iflist                        # ... return the list of candidate interfaces

  s_expr = [ f'{kw}={val}'                        # Collect the select expression data
              for (kw,val) in
                (('vrf',t_vrf),('type',t_type),('name',t_name),('linkid',t_linkid),('role',t_role),('af',t_af)) if val ]
  log.error(
    f'Cannot find a source interface for tunnel {t_intf.name} on node {ndata.name}',
    more_data=f'Specified filters: {", ".join(s_expr) or "none"}',
    category=log.MissingDependency,
    module='tunnel')

  return underlay_iflist

def set_tunnel_source(t_intf: Box, u_iflist: list, ndata: Box, topology: Box) -> bool:
  '''
  Set the tunnel interface _source parameters (ifname, optional AF)
  or report an error
  '''
  if u_iflist:
    u_intf = u_iflist[0]
    t_intf.tunnel._source.ifname = u_intf.ifname
    t_intf.tunnel._source.mtu = u_intf.get('mtu',ndata.get('mtu',1500))
    t_af = t_intf.get('tunnel.af',None)
    for af in log.AF_LIST:
      if (t_af is None or af == t_af) and af in u_intf:
        if isinstance(u_intf[af],str):                      # We need just IP addresses for numbered interfaces
          t_intf.tunnel._source[af] = str(ipaddress.ip_interface(u_intf[af]).ip)
        else:                                               # Or 'True' for unnumbered ones (if supported)
          t_intf.tunnel._source[af] = u_intf[af]

    return True

  msg_af = f'{t_intf.tunnel.af} ' if t_intf.get('tunnel.af',None) else ''
  linkname = _links.get_linkname(topology,t_intf.linkindex)
  t_src = get_empty_box()
  if 'vrf' in t_intf.tunnel:
    t_src.vrf = t_intf.tunnel.vrf
  if 'tunnel.source' in t_intf:
    t_src += t_intf.tunnel.source

  log.error(
    f'Cannot get {msg_af}tunnel source for link {linkname} on node {ndata.name}',
    more_data=f'Tunnel source data: {t_src or "none"}',
    category=log.MissingDependency,
    module='tunnel')

  return False

def set_tunnel_name(intf: Box, t_mode: str) -> None:
  if 'name' in intf and '->' in intf.name and t_mode not in intf.name:
    intf.name += f' [{t_mode} tunnel]'

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
  df_value = features.get(f'tunnel.{f_name}',None)
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
