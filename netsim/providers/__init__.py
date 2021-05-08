#
# Dynamic virtualization provider framework
# 
# Individual virtualization providers are defined in modules within this directory inheriting
# Provider class and replacing or augmenting its methods (most commonly, transform)
#

import platform
import subprocess
import os
import sys
import importlib
import inspect

# Related modules
from .. import common
from ..callback import Callback

class Provider(Callback):
  def __init__(self,provider,data):
    self.provider = provider
    if 'template' in data:
      self._default_template_name = data.template

  @classmethod
  def load(self,provider,data):
    module_name = __name__+"."+provider
    obj = self.find_class(module_name)
    if obj:
      return obj(provider,data)
    else:
      return Provider(provider,data)

  def get_template_path(self):
    return 'templates/provider/' + self.provider

  def get_output_name(self,fname,topology):
    if fname:
      return fname

    fname = topology.defaults.providers[self.provider].config
    if fname:
      return fname

    return "Vagrantfile"
  
  _default_template_name = "Vagrantfile.j2"

  def get_root_template(self):
    return self._default_template_name

  def transform(self,topology):
    processor_name = ""
    if platform.system() == "Windows":
        processor_name = platform.processor()
    elif platform.system() == "Darwin":
        processor_name = "intel"  # Assume Intel for MacOS
    elif platform.system() == "Linux":
        processor_name = subprocess.check_output("cat /proc/cpuinfo", shell=True).splitlines()[1].split()[2]
    if "processor" not in topology.defaults:
      topology.defaults.processor = processor_name

  def dump(self,topology):
    template_path = self.get_template_path()
    self.transform(topology)
    print("\nVagrantfile using templates from %s" % os.path.relpath(template_path))
    print("======================================================")
    print(common.template(self.get_root_template(),topology,template_path))

  def create(self,topology,fname):
    self.transform(topology)
    fname = self.get_output_name(fname,topology)
    with open(fname,"w") as output:
      output.write(common.template(self.get_root_template(),topology,self.get_template_path()))
      output.close()
      print("Created provider configuration file: %s" % fname)
