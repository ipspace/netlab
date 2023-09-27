'''
plugin - implement custom topology transformation plugins
'''

import os
import sys
import typing
import importlib
import importlib.util

from box import Box
from ..utils import log, read as _read
from ..utils.files import get_moddir
from .. import data
from . import config

'''
merge_plugin_defaults: Merge plugin defaults with topology defaults

We cannot simply overwrite the topology defaults with plugin defaults as the
defaults might have been changed by the user, so we're using a dirty trick:

* Topology defaults are augmented with plugin defaults (which means the global
  defaults take precedence)
* Whatever is really important should be in the 'important' dictionary and will
  take precedence over anything else
'''
def merge_plugin_defaults(defaults: typing.Optional[Box], topology: Box) -> None:
  if not defaults:
    return
  
  config.process_copy_requests(defaults)
  important_stuff = None
  if 'important' in defaults:
    important_stuff = defaults.important
    defaults.pop('important')

  topology.defaults = defaults + topology.defaults
  if important_stuff is not None:
    topology.defaults = topology.defaults + important_stuff

def load_plugin_from_path(path: str, plugin: str, topology: Box) -> typing.Optional[object]:
  module_path = path+'/'+plugin
  if not os.path.exists(module_path):
    if os.path.exists(module_path+'.py'):
      module_path = module_path+'.py'
    else:
      return None

  module: typing.Optional[object] = None
  config_name = None

  plugin_is_dir = os.path.isdir(module_path)
  if plugin_is_dir:
    dir_path = module_path
    module_path = module_path + '/plugin.py'
    config_name = plugin
    if not os.path.exists(module_path):
      return None

  module_name = plugin.replace('.py','')
  module_name = f'netlab.plugin.{module_name}'

  try:
    modspec  = importlib.util.spec_from_file_location(module_name,module_path)
    assert(modspec is not None)
    pymodule = importlib.util.module_from_spec(modspec)
    sys.modules[module_name] = pymodule
    assert(modspec.loader is not None)
    modspec.loader.exec_module(pymodule)
  except:
    print(f"Cannot load plugin {module_name} from {module_path}\n{str(sys.exc_info()[1])}")
    log.fatal('Aborting the transformation process','plugin')

  if config_name:
    setattr(pymodule,'config_name',config_name)

  if plugin_is_dir:
    defaults_file = dir_path + '/defaults.yml'
    if os.path.exists(defaults_file):
      merge_plugin_defaults(_read.read_yaml(defaults_file),topology)

  if log.VERBOSE:
    print(f"loaded plugin {module_name}")
  return pymodule

def init(topology: Box) -> None:
  data.types.must_be_list(parent=topology,key='defaults.plugin',path='',create_empty=True)    # defaults.plugin must be a list (if present)
  if topology.defaults.plugin:                                                                # If we have default plugins...
    data.types.must_be_list(parent=topology,key='plugin',path='',create_empty=True)           # ... make sure the plugin attribute is a list
    topology.plugin.extend(topology.defaults.plugin)                                          # ... and extend it with default plugins

  if not 'plugin' in topology:
    return

  topology.Plugin = []
  for pname in topology.plugin:                               # Iterate over all plugins
    search_path = ('.',str(get_moddir() / 'extra'))           # Search in current directory and 'extra' package directory
    for path in search_path:
      plugin = load_plugin_from_path(path,pname,topology)     # Try to load plugin from the current search path directory
      if plugin:                                              # Got it, get out of the loop
        break

    if plugin:                                                # If we found the plugin, add it to the list of active plugins
      topology.Plugin.append(plugin)
    else:
      log.error(f"Cannot find plugin {pname} in {search_path}",log.IncorrectValue,'plugin')

  if log.debug_active('plugin'):
    print(f'plug INIT: {topology.Plugin}')

def execute(action: str, topology: Box) -> None:
  if not 'Plugin' in topology:
    return

  for plugin in topology.Plugin:
    if hasattr(plugin,action):
      func = getattr(plugin,action)
      if log.debug_active('plugin'):
        print(f'plug INIT: {topology.Plugin}')
      func(topology)
