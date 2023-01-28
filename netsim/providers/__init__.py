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

# Related modules
from box import Box

from .. import common
from ..callback import Callback
from ..augment import devices
from ..data import get_from_box,get_box

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
    return str(common.get_moddir()) + '/' + self.get_template_path()

  def find_extra_template(self, node: Box, fname: str) -> typing.Optional[str]:
    return common.find_file(fname+'.j2',[ f'./{node.device}','.',f'{ self.get_full_template_path() }/{node.device}'])

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

    mappings = get_from_box(node,f'{self.provider}.{inkey}')
    if mappings:
      cur_binds = get_from_box(node,f'{self.provider}.{outkey}') or {}
      for file,mapping in mappings.items():
        if mapping in cur_binds.values():
          continue
        if not isinstance(mapping,str):
          common.error(
            f"Malformed extra file mapping for {self.provider}.{inkey}.{file} on node {node.name} -- should be string",
            common.IncorrectType,
            self.provider)
          continue

        if not self.find_extra_template(node,file):
          common.error(
            f"Cannot find template {file}.j2 for extra file {self.provider}.{inkey}.{file} on node {node.name}",
            common.IncorrectValue,
            self.provider)
          continue

        out_folder = f"{self.provider}_files/{node.name}"
        node[self.provider][outkey][f"{out_folder}/{file}"] = mapping

  def create_extra_files(
      self,
      node: Box,
      topology: Box,
      inkey: str = 'config_templates',
      outkey: str = 'binds') -> None:

    binds = get_from_box(node,f'{self.provider}.{outkey}')
    if not binds:
      return

    sys_folder = str(common.get_moddir())+"/"
    out_folder = f"{self.provider}_files/{node.name}"

    for file,mapping in binds.items():
      file_name = file.replace(out_folder+"/","")
      template_name = self.find_extra_template(node,file_name)
      if template_name:
        node_data = node + { 'hostvars': topology.nodes }
        common.write_template(
          in_folder=os.path.dirname(template_name),
          j2=os.path.basename(template_name),
          data=node_data.to_dict(),
          out_folder=out_folder, filename=file_name)
        print( f"Created {out_folder}/{file_name} from {template_name.replace(sys_folder,'')}, mapped to {node.name}:{mapping}" )

  def create(self, topology: Box, fname: typing.Optional[str]) -> None:
    self.transform(topology)
    fname = self.get_output_name(fname,topology)
    output = common.open_output_file(fname)
#    print(topology.nodes.to_yaml())
    output.write(common.template(self.get_root_template(),topology.to_dict(),self.get_template_path(),self.provider))
    if fname != '-':
      common.close_output_file(output)
      print("Created provider configuration file: %s" % fname)
      self.post_configuration_create(topology)
    else:
      output.write("\n")

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

        l[topology.provider].provider[node.provider] = True

  """
  Generic provider pre-output transform: remove loopback links
  """
  def pre_output_transform(self, topology: Box) -> None:
    if not 'links' in topology:
      return

    topology.links = [ link for link in topology.links if link.type != 'loopback' ]

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
      topology.nodes.pop(n,None)

  topology.links = [ l for l in topology.links if provider in l.provider ]      # Retain only the links used by current provider
  return topology
