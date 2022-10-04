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
from ..data import get_from_box
from ..callback import Callback
from ..augment.links import IFATTR
from ..augment import devices

# List of attributes we don't want propagated from defaults to global/node
#
no_propagate_list = ["attributes","extra_attributes","requires","supported_on","no_propagate","config_after","transform_after"]

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

"""
pre_transform: executed just before the main data model transformation is started

* Adjust global and node data structures
* Call module-specific node transformation code
* Call module-specific link transformation code
"""
def pre_transform(topology: Box) -> None:
  adjust_modules(topology)
  common.exit_on_error()

  check_module_parameters(topology)
  common.exit_on_error()

  module_transform("pre_transform",topology)
  node_transform("pre_transform",topology)
  link_transform("pre_transform",topology)

"""
pre/post_node_transform: executed just before/after the node data model transformation is started

"""
def pre_node_transform(topology: Box) -> None:
  module_transform("pre_node_transform",topology)
  node_transform("pre_node_transform",topology)
  link_transform("pre_node_transform",topology)

def post_node_transform(topology: Box) -> None:
  module_transform("post_node_transform",topology)
  node_transform("post_node_transform",topology)
  link_transform("post_node_transform",topology)

"""
pre/post_link_transform: executed just before/after the link data model transformation is started

"""
def pre_link_transform(topology: Box) -> None:
  module_transform("pre_link_transform",topology)
  node_transform("pre_link_transform",topology)
  link_transform("pre_link_transform",topology)

def post_link_transform(topology: Box) -> None:
  module_transform("post_link_transform",topology)
  node_transform("post_link_transform",topology)
  link_transform("post_link_transform",topology)

"""
post_transform:
  execute module-specific code after the main link- and node
  transformations has completed
"""
def post_transform(topology: Box) -> None:
  check_supported_node_devices(topology)       # A bit late, but we can do this check only after node data has been adjusted
  common.exit_on_error()
  copy_node_data_into_interfaces(topology)     # Copy node attributes that match interface attributes into interfaces
  module_transform("post_transform",topology)
  node_transform("post_transform",topology)
  link_transform("post_transform",topology)
  reorder_node_modules(topology)               # Make sure modules are configured in dependency order (#86)

# Set default list of modules for nodes without specific module list
#
def augment_node_module(topology: Box) -> None:
  if not 'module' in topology:
    return

  module = topology['module']
  for name,n in topology.nodes.items():
    if not 'module' in n and n.get('role') != 'host' and devices.get_device_attribute(n,'role',topology.defaults) != 'host':
      n.module = module

# Check whether the modules defined on individual nodes are valid module names
# and supported by the node device type
#
def check_supported_node_devices(topology: Box) -> None:
  for name,n in topology.nodes.items():
    for m in n.get("module",[]):                                # Iterate across all modules used by a node
      if not m in topology.defaults:                            # Do we know about the module?
        common.error(
          f"Unknown module {m} used by node {name}",
          common.IncorrectValue,
          'modules')
        continue
      mod_def = topology.defaults[m]                            # Get module defaults
      if mod_def and "supported_on" in mod_def :                # Are they sane and do they include supported device list?
        if not n.device in topology.defaults[m].supported_on:   # ... and is the device on the list?
          common.error(
            f"Device type {n.device} used by node {name} is not supported by module {m}",
            common.IncorrectValue,
            'modules')
          continue

# Merge global module parameters with per-node module parameters
#
# Remove "no_propagate" values (default: "attributes")
# before merging the global settings
#

def merge_node_module_params(topology: Box) -> None:
  for name,n in topology.nodes.items():
    if 'module' in n:
      for m in n.module:
        if not m in topology.defaults:      # Cannot propagate parameters of unknown module
          continue                          # ... error will be reported later
        if m in topology:
          global_settings = get_propagated_global_module_params(m,topology.get(m,{}),topology.defaults[m])
          if global_settings:
            n[m] = global_settings + n[m]

        dev_settings = devices.get_device_attribute(n,m,topology.defaults)
        if dev_settings:
          n[m] = get_propagated_global_module_params(m,dev_settings,topology.defaults[m]) + n[m]

        if isinstance(topology.defaults[m],dict):
          default_settings = get_propagated_global_module_params(m,topology.defaults[m],topology.defaults[m])
          if default_settings:
            n[m] = default_settings + n[m]

# Get propagated global parameters from settings (top-level or device-level)
#
# settings - dictionary with module settings
# mod_settings - default module settings
#
def get_propagated_global_module_params(module: str, settings: Box,mod_settings: Box) -> Box:
  global no_propagate_list

  global_copy = Box(settings)                  # Make a fresh copy of the settings
  no_propagate = list(no_propagate_list)       # ... and global no_propagate list
  if "no_propagate" in mod_settings:
    no_propagate.extend(mod_settings.no_propagate)
  no_propagate.extend([ k for k in mod_settings.keys() if "no_propagate" in k ])
  for remove_key in no_propagate:
    global_copy.pop(remove_key,None)
  return global_copy

'''
adjust_global_modules: last phase of global module adjustments

* add node-specific modules into global list of modules after the node
  modules have been set to default global values
* merge default settings with global settings
* copy global settings into node settings (apart from no_propagate attributes)
'''
def adjust_global_modules(topology: Box) -> None:
  mod_dict = { m : None for m in topology.get('module',[]) }
  for name,n in topology.nodes.items():
    for m in n.get('module',[]):
      mod_dict[m] = None

  if not mod_dict:
    return

  topology.module = list(mod_dict.keys())

"""
Merge default module parameters with global module parameters

A caveat: don't merge key specified in defaults "no_propagate" list --
forces us to do a deep copy of global parameters, and then eliminate
the ones we don't want.

We couldn't just iterate because we need a deep merge, and we can't remove
the no_propagate parameters from the global settings because they might be
needed in further transformation code.
"""

def merge_global_module_params(topology: Box) -> None:
  global no_propagate_list

  for m in topology.module:                                     # Iterate over all configured modules
    if not m in topology.defaults:                              # Does this module have defaults?
      common.error(
        f"Unknown module {m} (we found no system defaults for it)",
        common.IncorrectValue,
        'module')
      continue                                                  # Nope. Weird, but doesn't matter right now.
    mod_def = topology.defaults[m]
    if not isinstance(mod_def,dict):                               # Are module defaults a dict?
      common.fatal("Defaults for module %s should be a dict" % m)  # Nope? Too bad, crash right now, we can't live like that...

    default_copy = Box(mod_def)                                 # Got module defaults. Now copy them (we're gonna clobber them)
    no_propagate = list(no_propagate_list)                      # Always remove these default attributes (and make a fresh copy of the list)
    no_propagate.extend(default_copy.get("no_propagate", []))   # ... and whatever the module wishes to be removed
    no_propagate.extend([ k for k in mod_def.keys() if "no_propagate" in k ])
                                                                # ... including all attributes with 'no_propagate' in the name
    for remove_key in no_propagate:                             # We got the list of unwanted attributes.
      default_copy.pop(remove_key,None)                         # ... remove them with extreme prejudice

    if len(default_copy):                        # Anything left? Let's merge it with existing settings
      topology[m] = default_copy + topology[m]   # Have to use this convoluted way to prevent generating empty dict

  reorder_node_modules(topology,'transform_after')

'''
add_module_extra_parameters: add extra module keywords (ex: 'vrfs' for 'vrf' module) to the list of attributes
'''
def add_module_extra_parameters(topology: Box) -> None:
  if not 'module' in topology:
    return

  for m in topology.module:                                     # Iterate through the global list of modules
    if 'extra' in topology.defaults[m].attributes:              # Does the module have 'extra' parameters?
      for k in topology.defaults[m].attributes.extra.keys():    # ... oh, it does, iterate through its keys (attribute levels)
        for attr in topology.defaults[m].attributes.extra[k]:   # Take every attribute from the list of extra attributes
          if not attr in topology.defaults.attributes[k]:       # ... and if it's not already in the global list of attributes
            topology.defaults.attributes[k].append(attr)        # ... append it to the global list

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
  if not 'module' in topology:
    return
    
  module_transform("init",topology)
  merge_node_module_params(topology)
  merge_global_module_params(topology)
  add_module_extra_parameters(topology)
  check_module_parameters(topology)
  check_module_dependencies(topology)
  module_transform("pre_default",topology)
  node_transform("pre_default",topology)
  link_transform("pre_default",topology)
  if 'module' in topology:
    topology.defaults.module = topology.module

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
              common.error(
                "Invalid global %s attribute %s" % (m,k),
                common.IncorrectValue,
                'module')

  for name,n in topology.nodes.items():  # Inspect all nodes
    for m in n.get("module",[]):         # Iterate over all node modules
      if mod_attr[m] and m in n:         # Does the current module have a list of attributes?
                                         # ...Does node have module attribute?
        for k in n[m].keys():            # Iterate over node-level module-specific attributes
          if not k in mod_attr[m].node:  # If the name of an attribute is not in the list of allowed
                                         # ...node-level attributes report error
            common.error(
              f"Node {name}: invalid attribute {k} for module {m}",
              common.IncorrectValue,
              'module')

  for g in topology.get('groups',{}):                    # Inspect node_data in groups
    if 'node_data' in topology.groups[g]:
      for m in topology.get('module',[]):                # Iterate over global modules
        if m in topology.groups[g].node_data:            # Does the group node_data contain module attributes?
          for k in topology.groups[g].node_data[m]:      # Iterate over module-specific attributes in node_data
            if not k in mod_attr[m].node:                # Is the attribute a valid node attribute for the module?
              common.error(
                f"node_data in group {g} contains invalid attribute {k} for module {m}",
                common.IncorrectValue,
                'groups')

  for l in topology.get("links",[]):        # Inspect all links - use get to avoid instantiating links key
    for m in topology.get("module",[]):     # Iterate over all known modules - get avoids instantiating module key
      if m in l and mod_attr[m] and l[m]:   # ... focusing on modules that have attributes specified on this link
                                            # ... and want to have their attributes checked

        # Module attribute could be a list of keys or a class type
        #
        if isinstance(l[m],Box) and isinstance(mod_attr[m].link,list):
          for k in l[m].keys():             # Iterate over link-level module attributes
            if not k in mod_attr[m].link:   # If the name of an attribute is not in the list of allowed
                                            # ... link-level attributes, report an error
              common.error(
                f"Invalid attribute {k} for module {m} on link {l}",
                common.IncorrectValue,
                'modules')
        else:
          if type(l[m]).__name__ != str(mod_attr[m].link):
            common.error(
              f"Invalid value type for attribute {k} for module {m} on link {l}, expected {mod_attr[m].link}",
              common.IncorrectValue,
              'modules')


    for intf in l.interfaces:                     # Iterate over all interfaces attached to the link
      n = intf.node                               # ... get node name
      node = topology.nodes[n]                    # ... and node data structure (so the expressions don't get too crazy)
      for m in node.get("module",[]):             # Iterate over all node modules
        if mod_attr[m] and m in intf:             # Does the current module have a list of attributes?
                                                  # ... and interface contains module attributes?
          # Module attribute could be a list of keys or a class type
          #
          if isinstance(intf[m],Box) and isinstance(mod_attr[m].link,list):
            for k in intf[m].keys():              # Iterate over node link-level module-specific attributes
              if not k in mod_attr[m].interface:  # If the name of an attribute is not in the list of allowed
                                                  # ... interface attributes report error
                common.error(
                  f"Node {n} has invalid attribute {k} for module {m} on link {l}",
                  common.IncorrectValue,
                  'modules')
          else:
            if type(intf[m]).__name__ != str(mod_attr[m].interface) and not (intf[m] is False):
              common.error(
                f"Node {n} has invalid value type for module {m} on link {l}, expected {mod_attr[m].interface}",
                common.IncorrectValue,
                'modules')

"""
Prepare module attribute dictionary

* If the module attributes are a list, then global/node/link/interface attributes are the same

Otherwise:

* Add propagatable link attributes to interface attributes
* Copy global attributes to node attributes if the node attributes are not specified
"""

def parse_module_attributes(a: typing.Union[typing.Dict, Box]) -> Box:
  if isinstance(a,dict):
    attr = Box(a,default_box=True,box_dots=True)
    if not isinstance(attr.interface,str):
      attr.interface = list(set(attr.link) - set(attr.link_no_propagate) | set(attr.interface))
    attr.node = attr.get("node",attr["global"])
  else:
    attr = Box({
      "global": a,
      "node": a,
      "link": a,
      "interface": a
    },default_box=True,box_dots=True)
  return attr

"""
check_module_dependencies:

For every module used by the topology, check is the module has "requires" attribute, and if
it does, check that everything in that list is also in the topology modules list.
"""
def check_module_dependencies(topology:  Box) -> None:
  fcache: dict = {}

  for m in topology.get("module",[]):               # Use this format in case we don't use any modules
    mod_def = topology.defaults.get(m,{})           # Get module defaults
    if mod_def:                                     # Are they meaningful?
      mod_requires = topology.defaults[m].get('requires',[])
      for rqm in mod_requires:                      # Loop over prerequisite modules
        if not rqm in topology.module:              # Now we can be explicit - we know topology.modules exists
          common.error(
            f"Module {m} requires module {rqm} which is not enabled in your topology",
            common.MissingValue,
            'modules')

      for n in topology.nodes.values():                   # Now iterate over nodes and check device-specific requirements
        if not m in n.get('module',[]):                   # Is the module we're currently checking used by this node?
          continue                                        # ... nope, no worries, move on
        features = fcache.get(n.name) or \
                     devices.get_device_features(n,topology.defaults)
        fcache[n.name] = features                         # Get device features and save them in per-node cache
        if m in features:                                 # If the module has device feature flags, add device requirements to global ones
          node_requires = mod_requires + features[m].get('requires',[])
        else:
          node_requires = mod_requires                    # ... otherwise use global module requirements
        for rqm in node_requires:                         # Iterate over module requirements for this node (global + device-specific)
          if not rqm in n.get('module'):                  # ... is required module listed in the node?
            common.error(
              f"Module {m} on device {n.device} (node {n.name}) requires {rqm} module",
              common.IncorrectValue,
              'modules')

"""
reorder_node_modules:

For every node with at least two modules: sort the list of modules based on their _requires_ and
_config_after_/_transform_after_ dependencies preserving the original order as much as possible.
"""

def reorder_node_modules(topology: Box, secondary_sort: str = "config_after") -> None:
  if 'module' in topology:
    topology.module = sort_module_list(topology.module,topology.defaults, secondary_sort)
    topology.defaults.module = topology.module

  for name,n in topology.nodes.items():
    if 'module' in n:
      n.module = sort_module_list(n.module,topology.defaults, secondary_sort)

def sort_module_list(mods: list, mod_params: Box, secondary_sort: str = "config_after") -> list:
  if (len(mods) < 2):
    return mods

  output: typing.List[str] = []
  while len(mods):
    skipped: typing.List[str] = []
    for m in mods:
      if m in mod_params:
        requires = mod_params[m].get('requires',[]) + mod_params[m].get(secondary_sort,[])
        if [ r for r in requires if r in mods ]:
          skipped = skipped + [ m ]
        else:
          output = output + [ m ]

    mods = skipped

  return output

"""
Copy node data into interface data:

For every module configured on a node, merge attributes listed in node_copy list
from node data to interface data.

Example: copy node-level OSPF area into interfaces that don't have explicit area configuration.
"""

def copy_node_data_into_interfaces(topology: Box) -> None:
  for n in topology.nodes.values():
    for m in n.get('module',[]):                                 # Iterate over node modules
      mod_attr = topology.defaults[m].attributes                 # ... get a pointer to module attributes to make code easier to read
      if not mod_attr.node_copy:                                 # Any copyable attributes for this module?
        continue                                                 # ... nope, get out of here

      copy_attr = Box({ k: v
        for k,v in n.get(m,{}).items()
          if k in mod_attr.node_copy })                          # Build a Box of node attributes that could be copied to interfaces

      for intf in n.get('interfaces',[]):                        # We might have some work to do, iterate over all interfaces
        if not isinstance(intf.get(m,{}),dict):                  # ... if the interface module data is not a dict, we can't merge
          continue
        if 'vrf' in intf and mod_attr.vrf_aware:                 # Do we have to deal with VRF-aware attributes?
          vrf_attr = Box({ k: v
            for k,v in n.vrfs[intf.vrf].get(m,{}).items()
              if k in mod_attr.vrf_aware })                      # Build a Box of VRF attributes that could be copied to interfaces
        else:
          vrf_attr = Box({})                                     # ... otherwise set VRF attributes to an empty box

        if copy_attr or vrf_attr:                                # ... modify interface data only if we have something to merge
          intf[m] = copy_attr + vrf_attr + intf[m]

"""
get_effective_module_attribute:

Walk through the inheritance chain as supplied by the caller and extract desired module attribute
"""
def get_effective_module_attribute(
    path: str,
    intf: typing.Optional[Box] = None,
    link: typing.Optional[Box] = None,
    node: typing.Optional[Box] = None,
    topology: typing.Optional[Box] = None,
    defaults: typing.Optional[Box] = None,
    merge_dict: bool = True) -> typing.Optional[typing.Any]:

  composite_value: typing.Optional[Box] = None
  for obj in (intf,link,node,topology,defaults):
    if obj is None:
      continue
    value = get_from_box(obj,path)
    if not value:
      continue
    if not isinstance(value,Box) or not merge_dict:
      return value
    if composite_value:
      composite_value = value + composite_value
    else:
      composite_value = value

  return composite_value


"""
Callback transformation routines

* node_transform: for all nodes, call specified method for every module used by the node
* link_transform: for all links, call specified method for every module used by any node on the link

Note: mod_load is a global cache of loaded modules
"""

mod_load: typing.Dict = {}

def module_transform(method: str, topology: Box) -> None:
  global mod_load

  if common.debug_active('modules'):
    print(f'Processing module_{method} hooks')

  for m in topology.get('module',[]):
    if not mod_load.get(m):
      mod_load[m] = _Module.load(m,topology.get(m))
    if common.debug_active('modules'):
      if hasattr(mod_load[m],f"module_{method}"):
        print(f'Calling module {m} module_{method}')
    mod_load[m].call("module_"+method,topology)

def node_transform(method: str , topology: Box) -> None:
  global mod_load

  if common.debug_active('modules'):
    print(f'Processing node_{method} hooks')

  for name,n in topology.nodes.items():
    for m in n.get('module',[]):
      if not mod_load.get(m):  # pragma: no cover (module should have been loaded already)
        mod_load[m] = _Module.load(m,topology.get(m))
      if common.debug_active('modules'):
        if hasattr(mod_load[m],f"node_{method}"):
          print(f'Calling module {m} node_{method} on node {name}')
      mod_load[m].call("node_"+method,n,topology)

def link_transform(method: str, topology: Box) -> None:
  global mod_load

  if common.debug_active('modules'):
    print(f'Processing link_{method} hooks')

  for l in topology.get("links",[]):
    mod_list: typing.Dict = {}
    for node_data in l.get(IFATTR,[]):
      mod_list.update({ m: None for m in topology.nodes[node_data.node].get("module",[]) })
    for m in mod_list.keys():
      if not mod_load.get(m):  # pragma: no cover (module should have been loaded already)
        mod_load[m] = _Module.load(m,topology.get(m))
      if common.debug_active('modules'):
        if hasattr(mod_load[m],f"link_{method}"):
          print(f'Calling module {m} link_{method} on link {l.get("name","unnamed")}')
      mod_load[m].call("link_"+method,l,topology)
