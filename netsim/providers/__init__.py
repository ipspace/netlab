#
# Dynamic virtualization provider framework
#
# Individual virtualization providers are defined in modules within this directory inheriting
# Provider class and replacing or augmenting its methods (most commonly, transform)
#

import ipaddress
import os
import pathlib
import platform
import typing

# Related modules
from box import Box

from ..augment import devices, links
from ..data import append_to_list, filemaps, get_box, get_empty_box
from ..outputs.ansible import get_host_addresses
from ..utils import files as _files
from ..utils import log, strings, templates
from ..utils.callback import Callback


def get_cpu_model() -> str:
  processor_name = ""
  if platform.system() == "Windows":
    processor_name = platform.processor()
  elif platform.system() == "Darwin":
    processor_name = "arm64"          # Assume Apple silicon for MacOS
  elif platform.system() == "Linux":
    # This might fail on some Linux distributions, but it's a reasonable default
    try:
      processor_name = pathlib.Path("/proc/cpuinfo").read_text().splitlines()[1].split()[2]
    except Exception:
      processor_name = platform.processor()
  return processor_name.lower()

"""
The generic provider class. Used as a super class of all other providers
"""
class _Provider(Callback):
  SHARED_PREFIX = '-shared-'
  SHARED_SUFFIX = ':shared'
  READ_ONLY_SUFFIX = ':ro'

  def __init__(self, provider: str, data: Box) -> None:
    self.provider = provider
    if 'template' in data:
      self._default_template_name = data.template

  @classmethod
  def load(self, provider: str, data: Box) -> '_Provider':
    module_name = __name__+"."+provider
    obj = self.find_class(module_name)
    if obj:
      return obj(provider,data)
    else:
      return _Provider(provider,data)

  def get_template_path(self) -> str:
    return 'templates/provider/' + self.provider

  def get_full_template_path(self) -> str:
    return str(_files.get_moddir() / self.get_template_path())

  def find_extra_template(self, node: Box, fname: str, topology: Box) -> typing.Optional[str]:
    if fname in node.get('config',[]):                    # Are we dealing with extra-config template?
      path_prefix = topology.defaults.paths.custom.dirs
      path_suffix = [ fname ]
      fname = node.device
    else:
      path_suffix = [ node.device ]
      path_prefix = topology.defaults.paths.templates.dirs + [ self.get_full_template_path() ]

      if node.get('_daemon',False):
        if '_daemon_parent' in node:
          path_suffix.append(node._daemon_parent)
        path_prefix.append(str(_files.get_moddir() / 'daemons'))

    path = [ os.path.join(pf, sf) for pf in path_prefix for sf in path_suffix ]
    if log.debug_active('clab'):
      print(f'Searching for {fname}.j2 in {path}')

    found_file = _files.find_file(f'{fname}.j2', path)
    if log.debug_active('clab'):
      print(f'Found file: {found_file}')

    return found_file

  def get_output_name(self, fname: typing.Optional[str], topology: Box) -> str:
    if fname:
      return fname

    fname = topology.defaults.providers[self.provider].config
    if fname:
      return fname

    return "Vagrantfile"

  _default_template_name = "Vagrantfile.j2"

  def get_root_template(self) -> str:
    return self._default_template_name

  def node_image_version(self, topology: Box) -> None:
    for _,n in topology.nodes.items():
      if '.' in n.box:
        image_spec = n.box.split(':')
        n.box = image_spec[0]
        if len(image_spec) > 1:
          n.box_version = image_spec[1]

  def transform_node_images(self, topology: Box) -> None:
    pass

  def validate_node_image(self, node: Box, topology: Box) -> None:
    pass

  def transform(self, topology: Box) -> None:
    self.transform_node_images(topology)
    if "processor" in topology.defaults:
      return
    else:
      topology.defaults.processor = get_cpu_model()

  def create_extra_files_mappings(
      self,
      node: Box,
      topology: Box,
      inkey: str = 'config_templates',
      outkey: str = 'binds') -> None:

    mappings = node.get(f'{self.provider}.{inkey}',None)
    if not mappings:
      return
    
    map_dict = filemaps.mapping_to_dict(mappings)
    cur_binds = node.get(f'{self.provider}.{outkey}',[])
    bind_dict = filemaps.mapping_to_dict(cur_binds)
    base_path = pathlib.Path(f"{self.provider}_files")
    
    for file,mapping in map_dict.items():
      file = file.replace('@','.')
      # Check if mapping ends with :shared - if so, put it in the root provider folder
      if mapping.endswith(self.SHARED_SUFFIX):
        mapping = mapping.rsplit(self.SHARED_SUFFIX, 1)[0] + self.READ_ONLY_SUFFIX
        # Prefix shared files to avoid node name conflicts
        out_path = base_path / f"{self.SHARED_PREFIX}{file}" 
      else:
        out_path = base_path / node.name / file

      out_key = out_path.as_posix()
      if out_key in bind_dict:
        continue

      if not self.find_extra_template(node,file,topology):
        log.error(
          f"Cannot find template {file}.j2 for extra file {self.provider}.{inkey}.{file} on node {node.name}",
          category=log.IncorrectValue,
          module=self.provider)
        continue

      bind_dict[out_key] = mapping

    node[self.provider][outkey] = filemaps.dict_to_mapping(bind_dict)

  def create_extra_files(
      self,
      node: Box,
      topology: Box,
      outkey: str = 'binds') -> None:

    binds = node.get(f'{self.provider}.{outkey}',None)
    if not binds:
      return

    sys_folder = str(_files.get_moddir())+"/"

    bind_dict = filemaps.mapping_to_dict(binds)
    
    node_data = {
        **node.to_dict(),
        'hostvars': topology.nodes.to_dict(),
        'hosts': get_host_addresses(topology),
        'addressing': topology.addressing.to_dict()
    }

    base_path = pathlib.Path(f"{self.provider}_files")

    for file_str,mapping in bind_dict.items():
      full_out_path = pathlib.Path(file_str)

      # Only handle files placed under the provider's file directory
      try:
        full_out_path.relative_to(base_path)
      except ValueError:
        continue

      # We have to recover the template name from the final (local) file name
      # If the final file name is within the provider/node directory, the template
      # name is the rest of the path (which might be a file name or a relative path)
      # otherwise the template name is just the file name (used for shared files)
      #
      try:
        file_rel = str(full_out_path.relative_to(base_path / node.name))
      except ValueError:
        file_rel = full_out_path.name

      if not file_rel:
        # nothing to render
        continue

      # For shared files, extract the original file name (remove 'shared-' prefix)
      template_fname = strings.removeprefix(file_rel,self.SHARED_PREFIX)

      template_name = self.find_extra_template(node, template_fname, topology)
      if not template_name:
        log.error(f"Cannot find template for {file_rel} on node {node.name}",log.MissingValue,'provider')
        continue

      # Create parent dirs if needed
      full_out_path.parent.mkdir(parents=True,exist_ok=True)

      # If the file already exists (either shared or node-specific), skip re-rendering
      if full_out_path.exists():
        if not log.QUIET:
          strings.print_colored_text('[MAPPED]  ','bright_cyan','Mapped ')
          print(f"{str(full_out_path)} to {node.name}:{mapping} (from {template_name.replace(sys_folder,'')})")

        continue
      try:
        templates.write_template(
          in_folder=os.path.dirname(template_name),
          j2=os.path.basename(template_name),
          data=node_data,
          out_folder=str(full_out_path.parent),
          filename=full_out_path.name)
      except Exception as ex:
        log.fatal(
          text=f"Error rendering {template_name} into {file_rel}\n{strings.extra_data_printout(str(ex))}",
          module=self.provider)

      if not log.QUIET:
        strings.print_colored_text('[MAPPED]  ','bright_cyan','Mapped ')
        print(f"{str(full_out_path)} to {node.name}:{mapping} (from {template_name.replace(sys_folder,'')})")

  def create(self, topology: Box, fname: typing.Optional[str]) -> None:
    self.transform(topology)
    fname = self.get_output_name(fname,topology)
    tname = self.get_root_template()
    try:
      r_text = templates.render_template(
        data=topology.to_dict(),
        j2_file=tname,
        path=self.get_template_path(),
        extra_path=_files.get_search_path(self.provider))
    except Exception as ex:
      log.fatal(
        text=f"Error rendering {fname} from {tname}\n{strings.extra_data_printout(str(ex))}",
        module=self.provider)

    _files.create_file_from_text(fname,r_text)
    if fname != '-':
      log.status_created()
      print(f"provider configuration file: {fname}")
      self.post_configuration_create(topology)
    else:
      print("\n")

  def post_start_lab(self, topology: Box) -> None:
    pass

  def pre_start_lab(self, topology: Box) -> None:
    pass

  def pre_stop_lab(self, topology: Box) -> None:
    pass

  def post_stop_lab(self, topology: Box) -> None:
    pass

  def post_configuration_create(self, topology: Box) -> None:
    pass

  def get_lab_status(self) -> Box:
    return get_empty_box()
  
  def get_node_name(self, node: str, topology: Box) -> str:
    return node

  def set_tc(self, node: Box, topology: Box, intf: Box) -> None:
    n_provider = devices.get_provider(node,topology.defaults)
    log.warning(
      text=f'tc is not supported (node {node.name}, link {intf.name})',
      module=n_provider,
      flag=f'{n_provider}.tc')

  """
  Generic provider pre-transform processing: Mark multi-provider links
  """
  def pre_transform(self,topology : Box) -> None:
    if not 'links' in topology:
      return

    for l in topology.links:
      for intf in l.interfaces:
        node = topology.nodes[intf.node]
        if not 'provider' in node:
          continue

        p_name = topology.provider                          # Get primary and secondary provider
        s_name = node.provider                              # ... to make the rest of the code more readable
        if p_name == s_name:                                # ... nothing to do if they're the same
          continue

        l[p_name].provider[s_name] = True                   # Collect secondary link provider(s)
        if 'uplink' in l[p_name]:                           # ... and copy primary uplink to secondary uplink
          l[s_name].uplink = l[p_name].uplink

  """
  Generic provider pre-output transform: remove loopback links
  """
  def pre_output_transform(self, topology: Box) -> None:
    if not 'links' in topology:
      return

    topology.links = [
      link for link in topology.links if link.type not in links.VIRTUAL_INTERFACE_TYPES ]

"""
select_primary_provider: Find the top provider for the topology. For example, you can have
clab nodes under libvirt provider, but not vice versa
"""
def select_primary_provider(topology: Box) -> None:
  p_default = topology.provider

  # Build a set of all providers used in the topology
  p_set = { ndata.provider if 'provider' in ndata else p_default for ndata in topology.nodes.values() }
  if len(p_set) == 1:                             # Single-provider topology
    p_used = list(p_set)[0]
    if p_default != p_used:                       # ... but not using the (default) primary provider
      log.warning(
        text=f'Topology provider changed from {p_default} to {p_used}. Nodes are not affected',
        flag='providers.change',
        module='providers')
      topology.provider = p_used
      topology.defaults.provider = p_used
      return

  # Now build the list of providers that can be mixed (in relative order)
  p_mix_list = [ x for x in topology.defaults.const.multi_provider if x in p_set ]
  if not p_mix_list:                              # No relevant providers
    return
  
  # Select the top provider from that list
  p_top = p_mix_list[0]
  if p_top == p_default:
    return                                        # No need to change the top provider

  topology.provider = p_top                       # Change the top provider
  topology.defaults.provider = p_top
  for ndata in topology.nodes.values():           # Now set the explicit providers for all nodes that need it
    if not 'provider' in ndata:
      ndata.provider = p_default

  log.warning(
    text=f'Topology provider changed from {p_default} to {p_top}. Nodes are not affected',
    flag='providers.change',
    module='providers')

"""
Get a pointer to provider module. Cached in topology._Providers
"""
def get_provider_module(topology: Box, pname: str) -> _Provider:
  if not pname in topology._Providers:
    topology._Providers[pname] = _Provider.load(pname,topology.defaults.providers[pname])

  return topology._Providers[pname]

"""
Execute a topology-wide provider hook
"""
def execute(hook: str, topology: Box) -> None:
  p_module = get_provider_module(topology,topology.provider)
  p_module.call(hook,topology)

  for node in topology.nodes.values():
    execute_node(f'node_{hook}',node,topology)

"""
Execute a node-level provider hook
"""
def execute_node(hook: str, node: Box, topology: Box, **kwargs: typing.Any) -> typing.Any:
  node_provider = devices.get_provider(node,topology.defaults)
  p_module = get_provider_module(topology,node_provider)
  return p_module.call(hook,node,topology,**kwargs)

"""
Mark all nodes and links with relevant provider(s)
"""
def mark_providers(topology: Box) -> None:
  for n in topology.nodes.values():                 # Set 'provider' attribute on all nodes
    if 'provider' in n:
      continue

    n.provider = topology.provider

  for l in topology.links:                          # Set 'providers' attribute on all links
    for intf in l.interfaces:
      if intf.node not in topology.nodes:
        continue
      node = topology.nodes[intf.node]
      l.provider[node.provider] = True

"""
Select a subset of the topology -- links and nodes relevant to the current provider
"""
def select_topology(topology: Box, provider: str) -> Box:
  topology = get_box(topology)                      # Create a copy of the topology
  for n in list(topology.nodes.keys()):             # Remove all nodes not belonging to the current provider
    if topology.nodes[n].provider != provider:
      topology.nodes[n].unmanaged = True

  topology.links = [ l for l in topology.links if provider in l.provider ]      # Retain only the links used by current provider
  return topology

"""
get_forwarded_ports -- build a list of default provider forwarded ports for the specified node
"""
def get_provider_forwarded_ports(node: Box, topology: Box) -> list:
  p = devices.get_provider(node,topology.defaults)
  fmap = topology.defaults.providers[p].get('forwarded',{})     # Provider-specific forwarded ports
  if not fmap:                                                  # No forwarded ports?
    return []                                                   # ... return an empty list

  pmap = topology.defaults.ports                                # Mappings of port names into TCP numbers
  node_fp = []                                                  # Forwarded ports for the current node

  for fp,fstart in fmap.items():                                # Iterate over forwarded ports
    if not fp in pmap:                                          # Is the port we're trying to forward known to netlab?
      continue                                                  # ... nope, bad luck, move on
    node_fp.append([ fstart + node.id, pmap[fp]])               # Append [host,device] port mapping

  return node_fp

def node_add_forwarded_ports(node: Box, fplist: list, topology: Box) -> None:
  if not fplist:
    return

  p = devices.get_provider(node,topology.defaults)
  for port_map in fplist:                                       # Iterate over forwarded port mappings
    port_map_string = f'{port_map[0]}:{port_map[1]}'            # Build the provider-compatible map entry
    append_to_list(node[p],'ports',port_map_string)             # ... and add it to the list of forwarded ports

"""
validate_images -- check the images used by individual nodes against provider image repo
"""
def validate_images(topology: Box) -> None:
  for n_data in topology.nodes.values():
    execute_node('validate_node_image',n_data,topology)

  log.exit_on_error()

"""
validate_mgmt_ip -- Validate management IP addresses
"""
def validate_mgmt_ip(
      node: Box,
      provider: str,
      mgmt: Box,
      required: bool = False,
      v4only: bool = False) -> None:

  valid_af = ['ipv4'] if v4only else ['ipv4','ipv6']
  n_mgmt = node.mgmt
  node_af = [ n_af for n_af in n_mgmt.keys() if n_af in valid_af ]
  if not node_af and required:
    log.error(
      f'Node {node.name} must have {" or ".join(valid_af)} management address',
      category=log.MissingValue,
      module=provider)

  if not mgmt:
    return

  for af in ['ipv4','ipv6']:
    if af not in n_mgmt:
      continue
    m_addr = ipaddress.ip_interface(n_mgmt[af])
    pfx = mgmt.get(f'{af}_pfx',None)
    if pfx is None:
      log.error(
        f'Node {node.name} has an {af} management address, but the mgmt pool does not have an {af} prefix',
        category=log.IncorrectValue,
        module=provider)
    elif not m_addr.network.subnet_of(pfx):
      log.error(
        f'Management {af} address of node {node.name} ({n_mgmt[af]}) is not part of the management subnet',
        category=log.IncorrectValue,
        module=provider)

"""
Execute tc commands
"""
def execute_tc_commands(topology: Box) -> None:
  for ndata in topology.nodes.values():
    for intf in ndata.interfaces:
      if 'tc' not in intf:
        continue
      execute_node('set_tc',node=ndata,topology=topology,intf=intf)

"""
Apply tc netem parameters to the specified interface
"""
NETEM_KW_MAP = {
  'delay': ' delay {delay}ms {jitter}ms'
}

NETEM_SIMPLE_KW = [ 'loss', 'corrupt', 'duplicate', 'reorder', 'rate' ]

def tc_extract_netem_parameters(qdisc: str) -> str:
  if 'qdisc netem' not in qdisc:
    return ''

  if 'root refcnt' not in qdisc:
    log.error(f'Cannot parse netem qdisc parameters: {qdisc}')
    return ''

  params = qdisc.split('root refcnt')[1].strip(' \n')
  return ' '+params.split(' ',maxsplit=1)[1]

def tc_netem_set(intf: str, tc_data: Box, pfx: str = '') -> typing.Union[str,bool]:
  global NETEM_KW_MAP,NETEM_SIMPLE_KW
  from ..cli import external_commands

  netem_params = ''
  if 'jitter' in tc_data and 'delay' not in tc_data:        # Delay and jitter have to be specified
    tc_data.delay = 0                                       # ... in a single netem parameter
  if 'delay' in tc_data and 'jitter' not in tc_data:        # ... so we have to ensure both of them
    tc_data.jitter = 0                                      # ... are set at the same time

  for kw in tc_data:
    if kw in NETEM_SIMPLE_KW:
      netem_params += f' {kw} {tc_data[kw]}'
    elif kw in NETEM_KW_MAP:
      netem_params += NETEM_KW_MAP[kw].format(**tc_data)

  if 'sudo' not in pfx:
    pfx = 'sudo '+pfx
  qdisc = external_commands.run_command(
    cmd=pfx + f' tc qdisc show dev {intf}',
    ignore_errors=True,return_stdout=True,check_result=True)
  tc_action = tc_data.get('action',None)
  if isinstance(qdisc,str) and 'noqueue' not in qdisc:
    if tc_action == 'show':
      return tc_extract_netem_parameters(qdisc)
    if 'qdisc netem' not in qdisc or tc_action != 'modify' or not(netem_params):
      external_commands.run_command(
        cmd=pfx + f' tc qdisc del dev {intf} root',
        ignore_errors=True,return_stdout=True,check_result=True)
      tc_action = ''
    if not netem_params:
      return ' disabled'

  if netem_params:
    tc_action = 'change' if tc_action == 'modify' else 'add'
    status = external_commands.run_command(pfx + f' tc qdisc {tc_action} dev {intf} root netem'+netem_params)
    return netem_params if status else False
  else:
    return ''
