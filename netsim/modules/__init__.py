#
# Dynamic module transformation framework
#
# Individual configuration modules are defined as Python files within this directory inheriting
# Module class and adding transformation methods
#
import typing

from box import Box

# Related modules
from .. import common
from ..callback import Callback
from ..augment.nodes import rebuild_nodes_map

# List of attributes we don't want propagated from defaults to global/node
#
no_propagate_list = ["attributes","requires","supported_on","no_propagate"]

class _Module(Callback):

  def __init__(self, data: Box) -> None:
    pass

  @classmethod
  def load(self, module: str, data: Box) -> typing.Any:
    module_name = __name__+"."+module
    obj = self.find_class(module_name)
    if obj:
      return obj(data)
    else:
      return _Module(data)

  def set_af_flag(self, node: Box, model_data: Box) -> None:
    for af in ['ipv4','ipv6']:
      if af in node.loopback:        # Address family enabled on loopback?
        model_data[af] = True        # ... we need it in the module
        continue

      for l in node.get('links',[]): # Scan all links
        if af in l:                  # Do we have AF enabled on any of them?
          model_data[af] = True      # Found it - we need it the module
          continue


"""
pre_transform: executed just before the main data model transformation is started

* Adjust global and node data structures
* Call module-specific node transformation code
* Call module-specific link transformation code
"""
def pre_transform(topology: Box) -> None:
  adjust_modules(topology)
  check_module_parameters(topology)
  node_transform("pre_transform",topology)
  link_transform("pre_transform",topology)

"""
post_transform:
  execute module-specific code after the main link- and node
  transformations has completed
"""
def post_transform(topology: Box) -> None:
  check_supported_node_devices(topology)       # A bit late, but we can do this check only after node data has been adjusted
  node_transform("post_transform",topology)
  link_transform("post_transform",topology)

# Set default list of modules for nodes without specific module list
#
def augment_node_module(topology: Box) -> None:
  if not 'module' in topology:
    return

  module = topology['module']
  for n in topology.nodes:
    if not 'module' in n:
      n.module = module

# Check whether the modules defined on individual nodes are valid
# and supported
#
def check_supported_node_devices(topology: Box) -> None:
  for n in topology.nodes:
    for m in n.get("module",[]):                                # Iterate across all modules used by a node
      if not m in topology.defaults:                            # Do we know about the module?
        common.error("Unknown module %s used by node %s" %
                     (m,n.name),common.IncorrectValue)
        continue
      mod_def = topology.defaults[m]                            # Get module defaults
      if mod_def and "supported_on" in mod_def :                # Are they sane and do they include supported device list?
        if not n.device in topology.defaults[m].supported_on:   # ... and is the device on the list?
          common.error("Device type %s used by node %s is not supported by module %s" %
                       (n.device,n.name,m),common.IncorrectValue)
          continue

# Merge global module parameters with per-node module parameters
#
# Remove "no_propagate" values (default: "attributes")
# before merging the global settings
#
def merge_node_module_params(topology: Box) -> None:
  global no_propagate_list

  for n in topology.nodes:
    if 'module' in n:
      for m in n.module:
        if m in topology:
          global_copy = Box(topology[m])
          no_propagate = list(no_propagate_list)              # Make sure we're using a fresh copy of the list
          if "no_propagate" in topology.defaults.get(m,{}):
            no_propagate.extend(topology.defaults[m].no_propagate)
          for remove_key in no_propagate:
            global_copy.pop(remove_key,None)
          if len(global_copy):
            n[m] = global_copy + n[m]

'''
adjust_global_modules: last phase of global module adjustments

* add node-specific modules into global list of modules after the node
  modules have been set to default global values
* merge default settings with global settings
* copy global settings into node settings (apart from no_propagate attributes)
'''
def adjust_global_modules(topology: Box) -> None:
  mod_dict = { m : None for m in topology.get('module',[]) }
  for n in topology.nodes:
    for m in n.get('module',[]):
      mod_dict[m] = None

  if not mod_dict:
    return

  """
  Merge default module parameters with global module parameters

  A caveat: don't merge key specified in defaults "no_propagate" list --
  forces us to do a deep copy of global parameters, and then eliminate
  the ones we don't want.

  We couldn't just iterate because we need a deep merge, and we can't remove
  the no_propagate parameters from the global settings because they might be
  needed in further transformation code.
  """
  global no_propagate_list

  topology.module = list(mod_dict.keys())
  for m in topology.module:                                     # Iterate over all configured modules
    if not m in topology.defaults:                              # Does this module have defaults?
      continue                                                  # Nope. Weird, but doesn't matter right now.
    mod_def = topology.defaults[m]
    if not isinstance(mod_def,dict):                               # Are module defaults a dict?
      common.fatal("Defaults for module %s should be a dict" % m)  # Nope? Too bad, crash right now, we can't live like that...

    default_copy = Box(mod_def)                                 # Got module defaults. Now copy them (we're gonna clobber them)
    no_propagate = list(no_propagate_list)                      # Always remove these default attributes (and make a fresh copy of the list)
    no_propagate.extend(default_copy.get("no_propagate", []))   # ... and whatever the module wishes to be removed
    for remove_key in no_propagate:                             # We got the list of unwanted attributes.
      default_copy.pop(remove_key,None)                         # ... remove them with extreme prejudice

    if len(default_copy):                        # Anything left? Let's merge it with existing settings
      topology[m] = default_copy + topology[m]   # Have to use this convoluted way to prevent generating empty dict

'''
adjust_modules: somewhat intricate multi-step config module adjustments

* Set node default modules based on global modules
* Adjust global module list based on node modules + copy default settings into topology settings
* Check whether the module parameters specified globally, or on node/link level, are valid
* Merge global module parametres into nodes
'''
def adjust_modules(topology: Box) -> None:
  augment_node_module(topology)
  adjust_global_modules(topology)
  check_module_parameters(topology)
  check_module_dependencies(topology)
  module_transform("pre_default",topology)
  node_transform("pre_default",topology)
  link_transform("pre_default",topology)
  merge_node_module_params(topology)

"""
check_module_parameters:

Verify global, node, link, and node-on-link data for all modules
that include _attributes_ element in default settings

parse_module_attributes:

Accept list or dict as module attributes. List format applies to
all levels (global, node, link, node-on-link), dict format specifies
lists for every level.

Global attributes are used as default value for node attributes.
Link attributes are used as default value for node-on-link attributes.
"""

def check_module_parameters(topology: Box) -> None:
  mod_attr = Box({},default_box=True,box_dots=True)

  for m in topology.get("module",[]):                      # Iterate over all active modules
    mod_def = topology.defaults.get(m,{})                  # Get module defaults
    if mod_def:                                            # Did we get something meaningful?
      if "attributes" in topology.defaults.get(m,{}):      # ... and does it include "attributes"?
        mod_attr[m] = parse_module_attributes(topology.defaults[m].attributes)

        if topology.get(m,{}):                             # Now we can start: are there global module parameters in topology?
          for k in topology[m].keys():                     # Got them - iterate over them
            if not k in mod_attr[m]["global"]:             # Did we get a parameter that is not in global attributes? Jeez... barf
              common.error("Invalid global %s attribute %s" % (m,k),common.IncorrectValue)

  for n in topology.nodes:               # Inspect all nodes
    for m in n.get("module",[]):         # Iterate over all node modules
      if mod_attr[m] and m in n:         # Does the current module have a list of attributes?
                                         # ...Does node have module attribute?
        for k in n[m].keys():            # Iterate over node-level module-specific attributes
          if not k in mod_attr[m].node:  # If the name of an attribute is not in the list of allowed
                                         # ...node-level attributes report error
            common.error("Node %s: invalid attribute %s for module %s" % (n.name,k,m),common.IncorrectValue)

  rebuild_nodes_map(topology)
  for l in topology.get("links",[]):        # Inspect all links - use get to avoid instantiating links key
    for m in topology.get("module",[]):     # Iterate over all known modules - get avoids instantiating module key
      if m in l and mod_attr[m]:            # ... focusing on modules that have attributes specified on this link
                                            # ... and want to have their attributes checked
        for k in l[m].keys():               # Iterate over link-level module attributes
          if not k in mod_attr[m].link:     # If the name of an attribute is not in the list of allowed
                                            # ... link-level attributes, report an error
            common.error("Invalid attribute %s for module %s on link %s" % (k,m,l),common.IncorrectValue)

    for n in l.keys():                            # Iterate over all link attributes,
      if n in topology.nodes_map:                 # ... select those attributes that represent nodes
        node = topology.nodes_map[n]              # Get the node data structure (so the expressions don't get too crazy)
        for m in node.get("module",[]):           # Iterate over all node modules
          if mod_attr[m] and m in (l[n] or {}):   # Does the current module have a list of attributes?
                                                  # ... Does node have link-level module attributes?
                                                  # ... Caveat: l(n) could be None (thus the need for "or")
            for k in l[n][m].keys():              # Iterate over node link-level module-specific attributes
              if not k in mod_attr[m].link_node:  # If the name of an attribute is not in the list of allowed
                                                  # ... link-level node attributes report error
                common.error("Node %s has invalid attribute %s for module %s on link %s" % (n,k,m,l),common.IncorrectValue)

def parse_module_attributes(a: typing.Union[typing.Dict, Box]) -> typing.Union[typing.Dict, Box]:
  if isinstance(a,dict):
    attr = Box(a,default_box=True,box_dots=True)
    attr.link_node = attr.get("link_node",attr.link)
    attr.node = attr.get("node",attr["global"])
  else:
    attr = {
      "global": a,
      "node": a,
      "link": a,
      "link_node": a
    }
  return attr

"""
check_module_dependencies:

For every module used by the topology, check is the module has "requires" attribute, and if
it does, check that everything in that list is also in the topology modules list.
"""
def check_module_dependencies(topology:  Box) -> None:
  for m in topology.get("module",[]):               # Use this format in case we don't use any modules
    mod_def = topology.defaults.get(m,{})           # Get module defaults
    if mod_def:                                     # Are they meaningful?
      if "requires" in mod_def:                     # Do they include list of required modules?
        for rqm in topology.defaults[m].requires:   # Loop over prerequisites
          if not rqm in topology.module:            # Now we can be explicit - we know topology.modules exists
            common.error("Module %s requires module %s which is not enabled in your topology" % (m,rqm))

"""
Callback transformation routines

* node_transform: for all nodes, call specified method for every module used by the node
* link_transform: for all links, call specified method for every module used by any node on the link

Note: mod_load is a global cache of loaded modules
"""

mod_load: typing.Dict = {}

def module_transform(method: str, topology: Box) -> None:
  global mod_load

  for m in topology.get('module',[]):
    if not mod_load.get(m):
      mod_load[m] = _Module.load(m,topology.get(m))
    mod_load[m].call("module_"+method,topology)

def node_transform(method: str , topology: Box) -> None:
  global mod_load

  rebuild_nodes_map(topology)

  for n in topology.nodes:
    for m in n.get('module',[]):
      if not mod_load.get(m):
        mod_load[m] = _Module.load(m,topology.get(m))
      mod_load[m].call("node_"+method,n,topology)

def link_transform(method: str, topology: Box) -> None:
  global mod_load

  rebuild_nodes_map(topology)
  for l in topology.get("links",[]):
    mod_list: typing.Dict = {}
    for n in l.keys():
      if not n in topology.nodes_map:
        continue
      mod_list.update({ m: None for m in topology.nodes_map[n].get("module",[]) })
    for m in mod_list.keys():
      if not mod_load.get(m):
        mod_load[m] = _Module.load(m,topology.get(m))
      mod_load[m].call("link_"+method,l,topology)