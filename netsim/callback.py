"""
Generic dynamic loadable module framework

The Callback class defines two methods:

* load: tries to load a more specific module
* call: tries to call named method with specified parameters
"""

import importlib
import inspect
from . import common

class Callback():

  @classmethod
  def find_class(self,module_name):
    if common.VERBOSE:
      print("loading %s..." % module_name)
    try:
      module = importlib.import_module(module_name)
      for name,obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj,Callback):
          if common.VERBOSE:
            print("Found %s " % obj)
          return obj

    except (ImportError, AttributeError):
      if common.VERBOSE:
        print("Failed to load specific module")
      return None

  def call(self,name,*args,**kwargs):
    method = getattr(self,name,None)
    if method:
      method(*args, **kwargs)
