#
# Create Vagrantfile from collected topology data
#

import os
import sys
import importlib
import inspect

# Related modules
from . import common

class Provider:
  def __init__(self,provider,data):
    self.provider = provider
    if 'template' in data:
      self._default_template_name = data.template

  @classmethod
  def load(self,provider,data):
    module_name = '.'.join(__name__.split('.')[:-1])+".providers."+provider
    if common.VERBOSE:
      print("loading %s..." % module_name)
    try:
      module = importlib.import_module(module_name)
      for name,obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj,Provider):
          if common.VERBOSE:
            print("Found %s " % obj)
          return obj(provider,data)

    except (ImportError, AttributeError):
      if common.VERBOSE:
        print("Failed to load provider-specific module")
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
    pass

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
