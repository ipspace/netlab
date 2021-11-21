'''
plugin - implement custom topology transformation plugins
'''

import os
import sys
from box import Box
from importlib import import_module
from .. import common

def init(topology: Box) -> None:
  if not 'plugin' in topology:
  	return

  topology.Plugin = []
  sys.path = ["."] + sys.path
  for pname in topology.plugin:
  	try:

  	  plugin = import_module(pname)
  	except:
  	  print("Cannot load plugin %s\n%s" % (pname,str(sys.exc_info()[1])))
  	  common.fatal('Aborting the transformation process','plugin')
  	topology.Plugin.append(plugin)

  sys.path = sys.path[1:]

def execute(action: str, topology: Box) -> None:
  if not 'Plugin' in topology:
  	return

  for plugin in topology.Plugin:
  	if hasattr(plugin,action):
  	  func = getattr(plugin,action)
  	  func(topology)
