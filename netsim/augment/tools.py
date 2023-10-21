'''
Tool-related topology transformation functions
'''

import os
from box import Box

from ..utils import log
from .. import data
from ..data.validate import validate_attributes,get_object_attributes
from ..data.types import must_be_list,must_be_string,must_be_dict

"""
Check the 'tools' section of the topology file

* Tools section must be a dictionary
* Tool names must be present in defaults.tools
* Selected tool runtime must be valid
"""
def validate_tool_attributes(topology: Box) -> None:
  for tool in topology.tools.keys():                # Iterate over tools     
    must_be_dict(                                   # Make sure the tool configuration is a dictionary    
      parent=topology.tools,
      key=tool,path=f'topology.tools',
      create_empty=True,
      module='topology')
    if not isinstance(topology.tools[tool],dict):   # Skip if we have an error
      continue
    if not tool in topology.defaults.tools:         # Check that the tool is valid
      log.error(
        f'Invalid tool {tool}\n... valid tools are {",".join(topology.defaults.tools.keys())}',
        log.IncorrectValue,
        'topology')
      continue
    if not 'runtime' in topology.tools[tool]:       # Check that the tool has a runtime defined
      topology.tools[tool].runtime = 'docker'       # Default is Docker

"""
Merge tool defaults and tool-specific settings, then check that the runtime is valid
"""
def merge_tool_defaults(topology: Box) -> None:
  for tool in topology.tools.keys():
    tool_data = topology.defaults.tools[tool] + topology.tools[tool] 
    if not tool_data[tool_data.runtime] or not 'up' in tool_data[tool_data.runtime]:            
      valid_runtimes = [k for k in tool_data.keys() if 'up' in k ]
      log.error(
        f'Invalid runtime {tool_data.runtime} for tool {tool}\n... valid runtimes are {",".join(valid_runtimes)}',
        log.IncorrectValue,
        'topology')

"""
Copy entries from default.tools dictionary that have 'enabled' attribute set to True into topology.tools dictionary
"""
def copy_default_tools(topology: Box) -> None:
  for tname,tdata in topology.defaults.tools.items():
    if not tdata.get('enabled',False) is True:
      continue

    if tname in topology.tools:
      continue

    topology.tools[tname] = topology.defaults.tools[tname]

"""
Process topology tools:

* Do basic sanity checks so we don't crash further down the line
* Copy tools that are enabled by default into lab topology
* Validate tool attributes 
"""
def process_tools(topology: Box) -> None:
  if 'tools' in topology:
    try:
        must_be_dict(topology,'tools','',module='topology',abort=True)
    except:
        topology.pop('tools')
        return

  copy_default_tools(topology)
  if 'tools' in topology:
    validate_tool_attributes(topology)
    merge_tool_defaults(topology)
