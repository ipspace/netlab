#
# Create tool configurations
#
import typing

import os
import sys
from box import Box
from pathlib import Path

from . import _TopologyOutput,check_writeable
from ..tools import _ToolOutput
from .common import adjust_inventory_host
from ..utils import templates,strings,log
from ..utils import files as _files

def render_tool_config(tool: str, fmt: str, topology: Box) -> str:
    output_module = _ToolOutput.load(tool)
    if output_module:
      return output_module.write(topology,fmt)
    else:
      log.error(f'Cannot load tool-specific module tools.{tool}')
      return ""

def create_tool_config(tool: str, topology: Box) -> None:
  tdata = topology.defaults.tools[tool] + topology.tools[tool]
  if not tdata.get('config',[]):
    return
  
  topo_data = topology.copy()
  topo_data[tool] = tdata
  Path(f'./{tool}').mkdir(exist_ok=True)
  log.status_created()
  print(f'{tool} configuration directory')
  for config in tdata.config:
    if not 'dest' in config:
      log.error(f'No destination file specified for tool configuration\n... tool {tool}\n... config {config}')
      continue
    fname = f'{tool}/{config.dest}'
    if 'render' in config:
      config_text = render_tool_config(tool,config.render,topology)
      config_src  = f'rendering "{config.render}" format'
    elif 'template' in config:
      template = config.template
      try:
        config_text = templates.render_template(
                        j2_file=config.template,
                        data=topo_data,
                        path=f'tools/{tool}',
                        extra_path=_files.get_search_path(f'tools/{tool}'))
      except Exception as ex:
        log.fatal(
          text=f"Error rendering {config.template}\n{strings.extra_data_printout(str(ex))}",
          module='libvirt')
      config_src  = f'from {config.template} template'
    else:
      log.error(f'Unknown tool configuration type\n... tool {tool}\n... config {config}')
      continue

    try:
      _files.create_file_from_text(fname,config_text)
      log.status_created()
      print(f'{fname} {config_src}')
    except Exception as e:
      log.error(f'Error writing tool configuration file {fname}\n... {e}')

class ToolConfigs(_TopologyOutput):

  DESCRIPTION :str = 'Create configuration files for external tools'

  def write(self, topology: Box) -> None:
    if not 'tools' in topology:
      return

    if hasattr(self,'filenames'):
      log.error('Tools output module does not accept extra parameters')

    check_writeable('tools')
    topo_copy = topology.copy()
    for node in list(topo_copy.nodes.keys()):
      topo_copy.nodes[node] = adjust_inventory_host(
                                node=topo_copy.nodes[node],
                                defaults=topology.defaults,
                                ignore=[ 'name' ],
                                group_vars=True)
    for tool in topo_copy.tools.keys():
      create_tool_config(tool,topo_copy)
