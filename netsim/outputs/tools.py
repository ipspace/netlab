#
# Create tool configurations
#
import typing

import os
import sys
from box import Box
from pathlib import Path

from .. import common
from . import _TopologyOutput,check_writeable
from .common import adjust_inventory_host
from ..utils import templates

def create(nodes: Box, defaults: Box, addressing: typing.Optional[Box] = None) -> Box:
  inventory = Box({},default_box=True,box_dots=True)

  if addressing:
    inventory.all.vars.pools = addressing
    for name,pool in inventory.all.vars.pools.items():
      for k in list(pool.keys()):
        if ('_pfx' in k) or ('_eui' in k):
          del pool[k]

  for name,node in nodes.items():
    inventory[name] = adjust_inventory_host(
                        node = node,
                        defaults = defaults,
                        ignore = ['name'],
                        group_vars = True)

  return inventory

def write_yaml(data: Box, fname: str, header: str) -> None:
  dirname = os.path.dirname(fname)
  if dirname and not os.path.exists(dirname):
    os.makedirs(dirname)

  with open(fname,"w") as output:
    output.write(header)
    output.write(common.get_yaml_string(data))
    output.close()

def create_tool_config(tool: str, topology: Box) -> None:
  tdata = topology.defaults.tools[tool] + topology.tools[tool]
  if not tdata.get('config',[]):
    return
  
  topo_data = topology.copy()
  topo_data[tool] = tdata
  Path(f'./{tool}').mkdir(exist_ok=True)
  print(f'Created {tool} configuration directory')
  for config in tdata.config:
    if not 'dest' in config:
      common.error(f'No destination file specified for tool configuration\n... tool {tool}\n... config {config}')
      continue
    fname = f'{tool}/{config.dest}'
    if 'template' in config:
      config_text = templates.template(
                      j2=config.template,
                      data=topo_data,
                      path=f'tools/{tool}',
                      user_template_path=f'tools/{tool}')
      try:
        with open(fname,"w") as output:
          output.write(config_text)
          output.close()
        print(f'Created {fname} from template {config.template}')
      except Exception as e:
        common.error(f'Error writing tool configuration file {fname}\n... {e}')
    else:
      common.error(f'Unknown tool configuration type\n... tool {tool}\n... config {config}')

class ToolConfigs(_TopologyOutput):

  def write(self, topology: Box) -> None:
    if not 'tools' in topology:
      return

    if hasattr(self,'filenames'):
      common.error('Tools output module does not accept extra parameters')

    check_writeable('tools')
    topo_copy = topology.copy()
    for node in list(topo_copy.nodes.keys()):
      topo_copy.nodes[node] = adjust_inventory_host(
                                node=topo_copy.nodes[node],
                                defaults=topology.defaults,
                                group_vars=True)
    for tool in topo_copy.tools.keys():
      create_tool_config(tool,topo_copy)
