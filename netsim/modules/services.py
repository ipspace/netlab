#
# Network services module
#
from box import Box

from .. import data
from ..augment import devices
from ..utils import log
from . import _Module, _routing


def resolve_servers(node: Box, svc_data: Box, topology: Box, mod_attr: Box, svc_cache: Box) -> None:
  for kw in svc_data.keys():
    if kw not in mod_attr.clients:
      continue
    if 'server' not in svc_data[kw]:
      if kw not in svc_data.get('server',{}) and 'ipv4' not in svc_data[kw] and 'ipv6' not in svc_data[kw]:
        log.error(
          f'Node {node.name} has services.{kw} parameters, but is neither a client nor a server',
          more_hints=[
            f'Every node using {kw} services must have either services.{kw}.server or services.server.{kw} attribute',
            f'You can also specify {kw} server as services.{kw}.ipv4 or services.{kw}.ipv6 address'],
          category=log.MissingValue,
          module='services')
      continue

    for srv_name in svc_data[kw].server:
      if 'err_clients' in svc_cache[srv_name][kw]:
        data.append_to_list(svc_cache[srv_name][kw],'err_clients',node.name)
        continue

      srv_data = topology.nodes[srv_name]
      if not kw in srv_data.get(f'services.server',{}):
        svc_cache[srv_name][kw].err_clients = [ node.name ]
        continue

      cp_intf = svc_cache[srv_name].get('cp_intf',None)
      if cp_intf is None:
        cp_intf = _routing.get_remote_cp_endpoint(srv_data)
        svc_cache[srv_name].cp_intf = cp_intf

      node_af = node.get('af',{})
      af_found = False
      for svc_af in log.AF_LIST:
        if svc_af in node_af and svc_af in cp_intf and isinstance(cp_intf[svc_af],str):
          data.append_to_list(svc_data[kw],svc_af,cp_intf[svc_af].split('/')[0])
          af_found = True

      if not af_found:
        data.append_to_list(svc_cache[srv_name][kw],'err_af',node.name)

def check_feature_support(ndata: Box, svc_data: Box, topology: Box, mod_attr: Box) -> None:
  is_server = 'services.server' in ndata
  for kw in mod_attr.clients:
    if kw in svc_data:
      devices.check_optional_features(
        data=svc_data[kw],
        path=f'topology.nodes.{ndata.name}.services',
        node=ndata,
        topology=topology,
        attribute=f'services.{kw}',
        check_mode=devices.FC_MODE.BLACKLIST)
    if is_server and kw in svc_data.server:
      devices.check_optional_features(
        data=svc_data.server[kw],
        path=f'topology.nodes.{ndata.name}.services.server',
        node=ndata,
        topology=topology,
        attribute=f'services.server.{kw}',
        check_mode=devices.FC_MODE.BLACKLIST)

def print_client_server_errors(svc_cache: Box, mod_attr: Box) -> None:
  for kw in mod_attr.clients:
    for srv_name,srv_data in svc_cache.items():
      if 'err_clients' in srv_data[kw]:
        log.error(
          f'Node {srv_name} is not a {kw} server',
          category=log.IncorrectValue,
          more_data=f'Used by {kw} client(s) on node(s) '+','.join(srv_data[kw].err_clients))
      elif 'err_af' in srv_data[kw]:
        log.error(
          f'{kw} server {srv_name} has no address family in common with some of its clients',
          category=log.MissingDependency,
          more_data=f'Conflict with {kw} client(s) on node(s) '+','.join(srv_data[kw].err_af))

def check_vrf(ndata: Box,mod_attr: Box) -> None:
  for kw in mod_attr.clients:
    vrf_name = ndata.get(f'services.{kw}.transport_vrf',None)
    if vrf_name is None:
      continue
    if vrf_name not in ndata.get('vrfs',{}):
      log.error(
        f'VRF {vrf_name} used to reach {kw} server from node {ndata.name} is not present on that node',
        category=log.MissingDependency,
        module='services')

def set_dns_fields(ndata: Box) -> None:
  """
  Set extra fields to simplify DNS templates
  """
  dns_data = ndata.get('services.dns',{})
  if not dns_data:                                # No DNS services, nothing to do
    return
  srv_list = dns_data.get('ipv6',[]) + dns_data.get('ipv4',[])
  if not srv_list:                                # No DNS servers defined
    return
  dns_data._server_list = srv_list                # Set combined IPv4/IPv6 server list field
  if 'services.server.dns' not in ndata:          # Are we also a DNS server?
    dns_data._no_hosts = True                     # Nope, we can skip the "ip host" definitions

def disable_shared_hosts(ndata: Box) -> None:
  """
  Containers running a DNS client should not use shared /etc/hosts file
  """
  if 'clab' not in ndata:
    return

  if 'services.dns' not in ndata and 'services.server.dns' not in ndata:
    return

  if 'clab.config_templates.hosts' in ndata:
    ndata.clab.config_templates.hosts = ndata.clab.config_templates.hosts.replace(':shared','')

class Services(_Module):

  def module_post_transform(self, topology: Box) -> None:
    """
    network services node data transformation

    * Check feature support
    * Check client/server mappings
    * Check VRFs
    * Resolve server names into IPv4/IPv6 addresses
    """
    svc_nodes = []
    svc_cache = data.get_empty_box()
    mod_attr = topology.defaults.services.attributes

    for ndata in topology.nodes.values():
      svc_data = ndata.get('services',None)
      if not svc_data:
        continue

      svc_nodes.append(ndata)
      resolve_servers(ndata,svc_data,topology,mod_attr,svc_cache)
      set_dns_fields(ndata)
      disable_shared_hosts(ndata)
      check_feature_support(ndata,svc_data,topology,mod_attr)
      check_vrf(ndata,mod_attr)

    print_client_server_errors(svc_cache,mod_attr)
