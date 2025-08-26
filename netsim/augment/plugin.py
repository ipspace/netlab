'''
plugin - implement custom topology transformation plugins
'''

import importlib
import importlib.util
import os
import sys
import typing

from box import Box

from .. import data
from ..utils import log, strings
from ..utils import read as _read
from ..utils import sort as _sort
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

  config_name = None

  plugin_is_dir = os.path.isdir(module_path)                # Plugin name could specify a directory
  if plugin_is_dir:                                         # If we're dealing with a directory...
    dir_path = module_path
    config_name = None

    for fn in ('__init__.py','plugin.py'):                  # ... try to find the Python plugin file within that directory
      if not os.path.exists(dir_path+"/"+fn):
        continue

      config_name = plugin                                  # Remember plugin name as configuration directory name
      module_path = module_path + '/' + fn                  # Remember the path to the Python file

      if '__init__' in fn:
        module_name = f'netlab.extra.{plugin}'              # Deal with the plugin as a regular Python module
      else:
        module_name = f'netlab.plugin.{plugin}'             # ... old-style plugin, put it into separate module namespace

      break

    if config_name is None:                                 # Out of loop, did we find the Python file?
      return None                                           # ... nope, return failure

  else:                                                     # Plugin name is name of a Python file
    module_name = plugin.replace('.py','')
    module_name = f'netlab.plugin.{module_name}'            # Put the module into the 'plugin' module namespace

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
Load plugin: try to load the plugin from any of the search path directories
'''
def load_plugin(pname: str,topology: Box) -> typing.Optional[object]:
  for path in topology.defaults.paths.plugin:
    plugin = load_plugin_from_path(path,pname,topology)     # Try to load plugin from the current search path directory
    if plugin:                                              # Got it, get out of the loop
      return plugin

  return None

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

'''
find_preceding_config: Utility function for custom config dependency sort

The _sort.dependency routine needs a list of 'things' that have to be before the current 'thing' in the
sorted output. For custom configs, that means the list of all extra configs that appear 'before' the
current 'thing' in at least one of the nodes
'''

def find_preceding_configs(c: str, topology: Box) -> list:
  before_set: typing.Set[str] = set()

  for ndata in topology.nodes.values():                       # Iterate over all nodes (yeah, I know, we're in O(n^2) land at least)
    if not 'config' in ndata:                                 # ... but this should be fast
      continue
    cfg = ndata.config                                        # Cache the config attribute value (see also: premature optimization)
    if not c in cfg:                                          # current node not using the interesting config, move on
      continue

    before_set = before_set | set(cfg[:cfg.index(c)])         # Add all config requests before the current one to the before_set

  return list(before_set)                                     # After iterating through nodes, return the list of what we collected

'''
sort_extra_config: Sort topology-wide custom configs

Input:  'custom' config lists on nodes
Output: topology-wide list of custom configurations sorted in 'at least one node has them in this order' order
'''

def sort_extra_config(topology: Box) -> list:
  extra_set: typing.Set[str] = set()
  for ndata in topology.nodes.values():                       # Iterate over all nodes
    if not 'config' in ndata:                                 # Skip nodes without custom configs
      continue
    extra_set = extra_set | set(ndata.config)                 # and keep building the (unordered non-duplicate) set

  extra_list = list(extra_set)                                # Turn set of extra configs into an unordered list
  if not extra_list:                                          # If we got nothing useful, we were called by accident
    return []                                                 # ... tell the caller there's nothing to do

  return _sort.dependency(
            extra_list,
            lambda p: find_preceding_configs(p,topology))

'''
Initialize plugin subsystem:

* Merge default- and topology plugins
* Load all requested plugins (also checking the presence of their dependencies)
* Sort plugins based on their _execute_after dependencies
'''
def init(topology: Box) -> None:
  #
  # Initial sanity checks:
  # 
  # * defaults.plugin must be a list
  # * topology.plugin (when present or when we have default plugins) must be a list
  #
  data.types.must_be_list(parent=topology,key='defaults.plugin',path='',create_empty=True)
  if topology.defaults.plugin or 'plugin' in topology:
    data.types.must_be_list(parent=topology,key='plugin',path='',create_empty=True)
    topology.plugin.extend(topology.defaults.plugin)

  if not 'plugin' in topology:
    return

  topology.Plugin = []
  load_error = False
  for pname in list(topology.plugin):                         # Iterate over all plugins
    if not isinstance(pname,str):
      log.error(
        f"Plugin name must be a string, found {pname}",
        category=log.IncorrectValue,
        module='plugin')
      load_error = True
      continue

    plugin = load_plugin(pname,topology)                      # Try to load plugin from the search path

    if plugin:                                                # If we found the plugin...
      topology.Plugin.append(plugin)                          # ... and add it to the list of active plugins
    else:
      load_error = True
      log.error(
        f"Cannot find plugin {pname}",
        more_data = f"Search path:\n{strings.get_yaml_string(topology.defaults.paths.plugin)}",
        category=log.IncorrectValue,
        module='plugin')

  if load_error:                                              # Skip the rest of the code on error as it might crash
    return                                                    # ... due to discrepancy between lists of plugin names and loaded plugins

  sort_plugins(topology)
  if log.debug_active('plugin'):
    print(f'plug INIT: {topology.Plugin}')

'''
plugin_requires_check: given a plugin, check whether it has the _requires
attribute, whether that attribute is a list, and whether all plugins in that list
are included in the topology

check_plugin_dependencies: perform plugin_requires_check for all loaded plugins
'''

def plugin_requires_check(plugin: object, topology: Box) -> None:
  rq = getattr(plugin,'_requires',None)
  if rq is None:                                              # No dependencies, no worries
    return

  pname = getattr(plugin,'_config_name','plugin')             # Get plugin name for error messages
  if not isinstance(rq,list):                                 # _requires metadata must be a list
    log.error('plugin _requires metadata must be list',log.IncorrectType,pname)
    delattr(plugin,'_requires')                               # Remove the _requires metadata so it won't crash code using it
    return

  for dp in rq:                                               # Now test whether the prerequisite plugins are included
    if not dp in topology.plugin and not dp in topology.module:
      log.error(
        f"{pname} plugin requires {dp} {'module' if dp in topology.defaults else 'plugin'} which is not included in lab topology",
        log.MissingDependency,
        'plugin')

def check_plugin_dependencies(topology: Box) -> None:
  for plugin in topology.get('Plugin',[]):
    plugin_requires_check(plugin,topology)

'''
Execute the specified hook in a plugin
'''
def execute_plugin_hook(action: str, plugin: object, topology: Box) -> None:
  if hasattr(plugin,action):                                # Does the plugin have the required action?
    func = getattr(plugin,action)                           # ... yes, fetch the function to call
    if log.debug_active('plugin'):                          # ... do some logging to help the poor debugging souls
      print(f'plug {action}: {plugin}')
    func(topology)                                          # ... and execute the plugin function

'''
Execute a plugin action:

* Iterate over all plugins
* Try to get the 'action' attribute from the plugin
* If successful, execute it.
'''
def execute(action: str, topology: Box) -> None:
  if not 'Plugin' in topology:                                # No plugins, no worries
    return

  if log.debug_active('plugin'):
    print(f'plug hook: {action}')

  for plugin in topology.Plugin:                              # Iterate over the loaded plugin modules
    execute_plugin_hook(action,plugin,topology)               # ... and try to execute the hook
