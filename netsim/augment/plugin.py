'''
plugin - implement custom topology transformation plugins
'''

import os
import sys
import typing
import importlib
import importlib.util

from box import Box
from .. import common
from .. import data

def load_plugin_from_path(path: str, plugin: str) -> typing.Optional[object]:
  module_path = path+'/'+plugin
  if not os.path.exists(module_path):
    if os.path.exists(module_path+'.py'):
      module_path = module_path+'.py'
    else:
      return None

  module: typing.Optional[object] = None
  config_name = None

  if os.path.isdir(module_path):
    module_path = module_path + '/plugin.py'
    config_name = plugin
    if not os.path.exists(module_path):
      return None

  module_name = plugin.replace('.py','')
  module_name = f'netlab.plugin.{module_name}'

  try:
    modspec  = importlib.util.spec_from_file_location(module_name,module_path)
    assert(isinstance(modspec,importlib.machinery.ModuleSpec))
    pymodule = importlib.util.module_from_spec(modspec)
    sys.modules[module_name] = pymodule
    assert(isinstance(modspec.loader,importlib.abc.Loader))
    modspec.loader.exec_module(pymodule)
  except:
    print(f"Cannot load plugin {module_name} from {module_path}\n{str(sys.exc_info()[1])}")
    common.fatal('Aborting the transformation process','plugin')

  if config_name:
    setattr(pymodule,'config_name',config_name)

  if common.VERBOSE:
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
  for pname in topology.plugin:
    plugin = None
    search_path = ('.',common.netsim_package_path+'/extra')
    for path in search_path:
      if not plugin:
        plugin = load_plugin_from_path(path,pname)
    if plugin:
      topology.Plugin.append(plugin)
    else:
      common.error(f"Cannot find plugin {pname} in {search_path}",common.IncorrectValue,'plugin')

  if common.debug_active('plugin'):
    print(f'plug INIT: {topology.Plugin}')

def execute(action: str, topology: Box) -> None:
  if not 'Plugin' in topology:
    return

  for plugin in topology.Plugin:
    if hasattr(plugin,action):
      func = getattr(plugin,action)
      if common.debug_active('plugin'):
        print(f'plug INIT: {topology.Plugin}')
      func(topology)
