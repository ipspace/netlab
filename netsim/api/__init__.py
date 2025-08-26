#
# Plugin API routines
#
import typing

from box import Box

from ..data import append_to_list, global_vars
from ..data.types import must_be_list
from ..utils import log, strings

'''
get_config_name: get the name of configuration to be added to node.config attribute

This function is deprecated. Plugins should use 'global _config_name' instead.
'''
def get_config_name(g: dict) -> typing.Optional[str]:
  config_name = g.get('config_name',None)
  if config_name:
    return config_name

  log.fatal(f"Cannot get configuration template name for plugin { g.get('__file__') }",'plugin')
  return None

'''
node_config: add custom configuration item to the node.config list
'''
def node_config(node: Box, config_name: typing.Optional[str]) -> None:
  if not config_name:
    return

  append_to_list(node,'config',config_name)
  append_to_list(global_vars.get_topology(),'_plugin_config',config_name)

'''
Make sure an attribute is a list (not sure anyone uses this)
'''
def list_attribute(parent: Box, key: str, path: str) -> typing.Optional[list]:
  return must_be_list(parent,key,path)
