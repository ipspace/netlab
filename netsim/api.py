#
# Plugin API routines
#
import sys
import typing
import os

from box import Box

from . import common

def get_config_name(g: dict) -> typing.Optional[str]:
  config_name = g.get('config_name',None)
  if config_name:
    return config_name

  common.fatal("Cannot get configuration template name for plugin %s" % g.get('__file__'),'plugin')
  return None

def node_config(node: Box, config_name: typing.Optional[str]) -> None:
  if config_name:
    config = node.get('config',[])
    if not config_name in config:
      node.config =  config + [ config_name ]

def list_attribute(parent: Box, key: str, path: str) -> typing.Optional[list]:
  return common.must_be_list(parent,key,path)
