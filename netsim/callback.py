"""
Generic dynamic loadable module framework

The Callback class defines two methods:

* load: tries to load a more specific module
* call: tries to call named method with specified parameters
"""

import importlib
import inspect
import typing
import sys

from . import common

class Callback():

  @classmethod
  def find_class(self, module_name: str, abort: bool = False) -> typing.Optional[typing.Any]:
    if common.VERBOSE:
      print("loading %s..." % module_name)
    try:
      module = importlib.import_module(module_name)
      for name,obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj,Callback):
          if common.VERBOSE:
            print("... found %s " % obj)
          return obj
      return None

    except (ImportError, AttributeError):
      if abort:
        common.fatal(f"Failed to load specific module: {sys.exc_info()[1]}")
      else:
        print(f"Failed to load specific module: {sys.exc_info()[1]}")
      return None

  def call(self, name: str, *args: typing.Any, **kwargs: typing.Any) -> None:
    method = getattr(self,name,None)
    if method:
      method(*args, **kwargs)
