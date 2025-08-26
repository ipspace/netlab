#
# Implement global variables hidden within topology defaults
#
# Needed to support reentrant use of netsim modules (custom transformations or tests)
#

import typing

from box import Box

_topology: typing.Optional[Box] = None
_globals:  typing.Optional[Box] = None
_glob_dict: dict = {}

'''
init -- create 'globals' entry in 'topology.defaults' and save a pointer to it

It would be ideal to get a pointer to topology in every call to 'get', but
that's not realistic.
'''

def init(topology: Box) -> None:
  global _topology,_globals

  _topology = topology
  _globals  = topology.defaults._globals


'''
get -- get a pointer to a global Box (referenced by name) hidden in topology
'''

def missing_globals(varname: str) -> typing.NoReturn:
  from ..utils.log import fatal
  fatal(f'Trying to use global variable {varname} before the global_vars subsystem is initialized')

def get(varname: str) -> Box:
  global _globals
  if _globals is None:
    missing_globals(varname)

  return _globals[varname]

def set(varname: str, value: typing.Any) -> None:
  global _globals
  if _globals is None:
    missing_globals(varname)

  _globals[varname] = value

def get_result_dict(varname: str) -> Box:
  global _glob_dict
  return _glob_dict.get(varname,Box({}))

def set_result_dict(varname: str, value: Box) -> None:
  global _glob_dict
  _glob_dict[varname] = value

def get_topology() -> typing.Optional[Box]:
  global _topology

  return _topology

def get_const(varname: str, default: typing.Any = None) -> typing.Any:
  topology = get_topology()
  if topology is None:
    return default

  return topology.defaults.const.get(varname, default)
