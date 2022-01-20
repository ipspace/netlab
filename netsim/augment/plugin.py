'''
plugin - implement custom topology transformation plugins
'''

import os
import sys
import typing

from box import Box
from importlib import import_module
from .. import common

def load_plugin_from_path(path: str, plugin: str) -> typing.Optional[object]:
  module_path = path+'/'+plugin
  module_name = module_path
  module: typing.Optional[object] = None
  is_package = os.path.isdir(module_path)
  config_name = None

  if is_package:
    sys.path = [ module_path ] + sys.path
    module_name = module_path + '/plugin.py'
    config_name = plugin
    plugin = 'plugin'
  else:
    sys.path = [ path ] + sys.path
    if os.path.exists(module_name+'.py'):
      module_name = module_name + '.py'

  if os.path.exists(module_name):
    try:
      module = import_module(plugin)
    except:
      print("Cannot load plugin %s\n%s" % (module_name,str(sys.exc_info()[1])))
      common.fatal('Aborting the transformation process','plugin')

    if is_package:
      setattr(module,'config_name',config_name)
  else:
    module = None

  sys.path = sys.path[1:]
  if common.VERBOSE:
    print("loaded plugin %s" % module)
  return module

def init(topology: Box) -> None:
  if not 'plugin' in topology:
    return

  topology.Plugin = []
  for pname in topology.plugin:
    plugin = None
    search_path = ('.',common.netsim_package_path+'/extra',pname)
    for path in search_path:
      if not plugin:
        plugin = load_plugin_from_path(path,pname)
    if plugin:
      topology.Plugin.append(plugin)
    else:
      common.error(f"Cannot find plugin {pname} in {search_path}",common.IncorrectValue,'plugin')

def execute(action: str, topology: Box) -> None:
  if not 'Plugin' in topology:
    return

  for plugin in topology.Plugin:
  	if hasattr(plugin,action):
  	  func = getattr(plugin,action)
  	  func(topology)
