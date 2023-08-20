#
# Graphite output module has been migrated into a tool renderer
#
# This skeleton module generates a fatal error message to tell the user
# to start using Graphite tool
#
import sys

from box import Box
from . import _TopologyOutput

class Graphite(_TopologyOutput):

  def write(self, topology: Box) -> None:
    print('''
The graphite output module is deprecated, please use netlab 'graphite' tool to
start graphite -- add the following lines to your lab topology:

tools:
  graphite:

You'll find more details in "Lab Topology Reference" -> "Integrating External
Tools" documentation section.
''')
    sys.exit(1)
