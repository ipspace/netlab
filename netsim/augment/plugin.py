'''
plugin - implement custom topology transformation plugins
'''

import os
import sys
import typing
import importlib
import importlib.util

from box import Box
from ..utils import log, read as _read, sort as _sort, strings
from ..utils.files import get_moddir,get_search_path
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
    print(f"Failed to load plugin {module_name} from {module_path}\nError reported by module loader: {str(sys.exc_info()[1])}")
    log.fatal('Aborting the transformation process','plugin')

  redirect = getattr(pymodule,'_redirect',None)
  if isinstance(redirect,str):
    topology.plugin = [ redirect if p == plugin else p for p in topology.plugin ]
    return load_plugin_from_path(path,redirect,topology)

  if config_name:
    setattr(pymodule,'config_name',config_name)
    setattr(pymodule,'_config_name',config_name)

  if plugin_is_dir:
    defaults_file = dir_path + '/defaults.yml'
    if os.path.exists(defaults_file):
      merge_plugin_defaults(_read.read_yaml(defaults_file),topology)

  if log.VERBOSE:
    print(f"loaded plugin {module_name}")
  return pymodule

'''
check_plugin_dependencies: given a plugin, check whether it has the _requires
attribute, whether that attribute is a list, and whether all plugins in that list
are included in the topology
'''

def check_plugin_dependencies(plugin: object, topology: Box) -> None:
  rq = getattr(plugin,'_requires',None)
  if rq is None:                                              # No dependencies, no worries
    return
  
  pname = getattr(plugin,'_config_name','plugin')             # Get plugin name for error messages
  if not isinstance(rq,list):                                 # _requires metadata must be a list
    log.error('plugin _requires metadata must be list',log.IncorrectType,pname)
    delattr(plugin,'_requires')                               # Remove the _requires metadata so it won't crash code using it
    return
  
  for dp in rq:                                               # Now test whether the prerequisite plugins are included
    if not dp in topology.plugin:
      log.error(f'{pname} requires plugin {dp} which is not included in lab topology',log.MissingValue,'plugin')

'''
Sort plugins based on their _requires and _execute_after attributes

Input:
* List of plugins in topology.plugin
* Loaded plugins (in the same order) in topology.Plugin

The sorting function has to build a dictionary of plugin modules, sort the plugin names,
and rebuild the list of loaded plugins.
'''
def sort_plugins(topology: Box) -> None:
  if not topology.get('plugin',[]):                           # No plugins, no sorting ;)
    return

  pmap: dict = {}
  for (idx,p) in enumerate(topology.plugin):                  # Build the name-to-module mappings
    pmap[p] = topology.Plugin[idx]

  # Sort the plugin names based on their dependencies
  topology.plugin = _sort.dependency(
                      topology.plugin,
                      lambda p: getattr(pmap[p],'_requires',[]) + getattr(pmap[p],'_execute_after',[]))
  topology.Plugin = [ pmap[p] for p in topology.plugin ]      # And rebuild the list of plugin modules

def init(topology: Box) -> None:
  data.types.must_be_list(parent=topology,key='defaults.plugin',path='',create_empty=True)    # defaults.plugin must be a list (if present)
  if topology.defaults.plugin:                                                                # If we have default plugins...
    data.types.must_be_list(parent=topology,key='plugin',path='',create_empty=True)           # ... make sure the plugin attribute is a list
    topology.plugin.extend(topology.defaults.plugin)                                          # ... and extend it with default plugins

  if not 'plugin' in topology:
    return

  topology.Plugin = []
  load_error = False
  search_path = get_search_path(pkg_path_component='extra')   # Search the usual places plus the 'extra' package directory
  for pname in list(topology.plugin):                         # Iterate over all plugins
    for path in search_path:
      plugin = load_plugin_from_path(path,pname,topology)     # Try to load plugin from the current search path directory
      if plugin:                                              # Got it, get out of the loop
        break

    if plugin:                                                # If we found the plugin...
      check_plugin_dependencies(plugin,topology)              # ... check its dependencies
      topology.Plugin.append(plugin)                          # ... and add it to the list of active plugins
    else:
      load_error = True
      log.error(
        f"Cannot find plugin {pname}\nSearch path:\n{strings.get_yaml_string(search_path)}",
        log.IncorrectValue,
        'plugin')

  if load_error:                                              # Skip the rest of the code on error as it might crash
    return                                                    # ... due to discrepancy between lists of plugin names and loaded plugins

  sort_plugins(topology)
  if log.debug_active('plugin'):
    print(f'plug INIT: {topology.Plugin}')

def execute(action: str, topology: Box) -> None:
  if not 'Plugin' in topology:
    return

  for plugin in topology.Plugin:
    if hasattr(plugin,action):
      func = getattr(plugin,action)
      if log.debug_active('plugin'):
        print(f'plug {action}: {plugin}')
      func(topology)
