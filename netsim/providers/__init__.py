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

  def create(self, topology: Box, fname: typing.Optional[str]) -> None:
    self.transform(topology)
    fname = self.get_output_name(fname,topology)
    output = common.open_output_file(fname)
    output.write(common.template(self.get_root_template(),topology.to_dict(),self.get_template_path()))
    if fname != '-':
      common.close_output_file(output)
      print("Created provider configuration file: %s" % fname)
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
