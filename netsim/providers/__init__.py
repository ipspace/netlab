#
# Dynamic virtualization provider framework
#
# Individual virtualization providers are defined in modules within this directory inheriting
# Provider class and replacing or augmenting its methods (most commonly, transform)
#

import platform
import subprocess
import os
import typing
import pathlib

# Related modules
from box import Box

from ..utils.callback import Callback
from ..augment import devices,links
from ..data import get_box,get_empty_box,filemaps
from ..utils import files as _files
from ..utils import templates,log,strings

class _Provider(Callback):
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
    return str(_files.get_moddir()) + '/' + self.get_template_path()

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

    path = [ pf + "/" + sf for pf in path_prefix for sf in path_suffix ]
    if log.debug_active('clab'):
      print(f'Searching for {fname}.j2 in {path}')

    found_file = _files.find_file(fname+'.j2',path)
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
    for name,n in topology.nodes.items():
      if '.' in n.box:
        image_spec = n.box.split(':')
        n.box = image_spec[0]
        if len(image_spec) > 1:
          n.box_version = image_spec[1]

  def transform_node_images(self, topology: Box) -> None:
    pass

  def transform(self, topology: Box) -> None:
    self.transform_node_images(topology)
    if "processor" in topology.defaults:
      return
    else:
      processor_name = ""
      if platform.system() == "Windows":
        processor_name = platform.processor()
      elif platform.system() == "Darwin":
        processor_name = "intel"  # Assume Intel for MacOS
      elif platform.system() == "Linux":
        processor_name = str(subprocess.check_output("cat /proc/cpuinfo", shell=True).splitlines()[1].split()[2])
      topology.defaults.processor = processor_name

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
    for file,mapping in map_dict.items():
      file = file.replace('@','.')
      if file in bind_dict:
        continue
      if not self.find_extra_template(node,file,topology):
        log.error(
          f"Cannot find template {file}.j2 for extra file {self.provider}.{inkey}.{file} on node {node.name}",
          category=log.IncorrectValue,
          module=self.provider)
        continue

      out_folder = f"{self.provider}_files/{node.name}"
      bind_dict[f"{out_folder}/{file}"] = mapping         # note: node_files directory is flat

    node[self.provider][outkey] = filemaps.dict_to_mapping(bind_dict)

  def create_extra_files(
      self,
      node: Box,
      topology: Box,
      inkey: str = 'config_templates',
      outkey: str = 'binds') -> None:

    binds = node.get(f'{self.provider}.{outkey}',None)
    if not binds:
      return

    sys_folder = str(_files.get_moddir())+"/"
    out_folder = f"{self.provider}_files/{node.name}"

    bind_dict = filemaps.mapping_to_dict(binds)
    for file,mapping in bind_dict.items():
      if not out_folder in file:                  # Skip files that are not mapped into the temporary provider folder
        continue
      file_name = file.replace(out_folder+"/","")
      template_name = self.find_extra_template(node,file_name,topology)
      if template_name:
        node_data = node + { 'hostvars': topology.nodes }
        if '/' in file_name:                      # Create subdirectory in out_folder if needed
          pathlib.Path(f"{out_folder}/{os.path.dirname(file_name)}").mkdir(parents=True,exist_ok=True)
        try:
          templates.write_template(
            in_folder=os.path.dirname(template_name),
            j2=os.path.basename(template_name),
            data=node_data.to_dict(),
            out_folder=out_folder, filename=file_name)
        except Exception as ex:
          log.fatal(
            text=f"Error rendering {template_name} into {file_name}\n{strings.extra_data_printout(str(ex))}",
            module=self.provider)

        strings.print_colored_text('[MAPPED]  ','bright_cyan','Mapped ')
        print(f"{out_folder}/{file_name} to {node.name}:{mapping} (from {template_name.replace(sys_folder,'')})")
      else:
        log.error(f"Cannot find template for {file_name} on node {node.name}",log.MissingValue,'provider')

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
def execute_node(hook: str, node: Box, topology: Box) -> None:
  node_provider = devices.get_provider(node,topology.defaults)
  p_module = get_provider_module(topology,node_provider)
  p_module.call(hook,node,topology)

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
#      topology.nodes.pop(n,None)

  topology.links = [ l for l in topology.links if provider in l.provider ]      # Retain only the links used by current provider
  return topology

"""
get_forwarded_ports -- build a list of forwarded ports for the specified node
"""
def get_forwarded_ports(node: Box, topology: Box) -> list:
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
