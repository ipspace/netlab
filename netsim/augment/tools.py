'''
Tool-related topology transformation functions
'''

from box import Box

from .. import data
from ..utils import log

"""
Check the 'tools' section of the topology file
(assuming global type validation made sure we have dicts where needed)

* Tool names must be present in defaults.tools
* Selected tool runtime must be valid
"""
def validate_tool_attributes(topology: Box) -> None:
  for tool in topology.tools.keys():                # Iterate over tools     
    if not tool in topology.defaults.tools:         # Check that the tool is valid
      log.error(
        f'Invalid tool {tool}',
        log.IncorrectValue,
        'topology',
        more_hints=f'valid tools are {",".join(topology.defaults.tools.keys())}',
        doc_url='extools/#extools-list')
      continue
    if not 'runtime' in topology.tools[tool]:       # Check that the tool has a runtime defined
      topology.tools[tool].runtime = 'docker'       # Default is Docker

"""
Merge tool defaults and tool-specific settings, then check that the runtime is valid
"""
def merge_tool_defaults(topology: Box) -> None:
  for tool in topology.tools.keys():
    if tool not in topology.defaults.tools:         # Invalid tool, reported in validate_tool_attributes
      continue
    tool_data = topology.defaults.tools[tool] + topology.tools[tool] 
    if not tool_data[tool_data.runtime] or not 'up' in tool_data[tool_data.runtime]:            
      valid_runtimes = [k for k,v in tool_data.items() if isinstance(v,dict) and 'up' in v ]
      log.error(
        f'Invalid runtime {tool_data.runtime} for tool {tool}',
        log.IncorrectValue,
        'topology',
        more_hints=f'valid runtimes are {",".join(valid_runtimes)}',
        doc_url='extools/#tools-intro')

"""
Get the list of active tools: tools specified in the lab topology and tools enabled by default
"""
def active_tools(topology: Box) -> list:
  t_list = list(topology.get('tools',{}).keys())            # Do not create an empty 'tools' dictionary
  t_list += [ t for t,t_data in topology.defaults.tools.items()
                if t not in t_list and t_data.get('enabled',False) is True ]
  return t_list

"""
Copy entries from default.tools dictionary that have 'enabled' attribute set to True into topology.tools dictionary
"""
def copy_default_tools(topology: Box) -> None:
  for tname in active_tools(topology):
    if tname in topology.tools:
      continue

    topology.tools[tname] = topology.defaults.tools[tname]

"""
Add plugins specified in the 'plugin' attribute of active tools to the list of topology plugins

This function is called before the plugins are loaded, and thus before the topology
attributes are validated. It ignores invalid data; the errors are reported later.
"""
def add_tool_plugins(topology: Box) -> None:
  try:
    for tname in active_tools(topology):
      if tname not in topology.defaults.tools:              # Invalid tool, reported later (do not create an empty
        continue                                            # ... defaults.tools entry that would hide the error)
      p_list = (topology.defaults.tools[tname] + (topology.tools.get(tname,{}) or {})).plugin
      if p_list:
        data.append_to_list(topology,'plugin',p_list,flatten=True)
  except Exception:                                         # Invalid data structures are reported later
    pass

"""
Process topology tools:

* Do basic sanity checks so we don't crash further down the line
* Copy tools that are enabled by default into lab topology
* Validate tool attributes 
"""
def process_tools(topology: Box) -> None:
  if log.pending_errors():                      # Skip tool processing if we already have pending errors
    return                                      # ... data structures might be broken

  copy_default_tools(topology)
  if 'tools' in topology:
    validate_tool_attributes(topology)
    merge_tool_defaults(topology)
