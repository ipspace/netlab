#
# Dump transformed topology in JSON format
#
# This is just a placeholder module (because we have to load something),
# the real work is done in the YAML module which tests for class name and
# prints out YAML or JSON string
#
from .yaml import YAML

class JSON(YAML):
  DESCRIPTION :str = 'Inspect transformed data in JSON format'

  pass
