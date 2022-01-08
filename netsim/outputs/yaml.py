#
# Create YAML or JSON output
#
import typing

import yaml
import os
from box import Box

from .. import common
from ..augment import topology

from . import _TopologyOutput

class YAML(_TopologyOutput):

  def write(self, topo: Box) -> None:
    outfile = self.settings.filename or '-'
    modname = type(self).__name__

    if hasattr(self,'filenames'):
      outfile = self.filenames[0]
      if len(self.filenames) > 1:
        common.error('Extra output filename(s) ignored: %s' % str(self.filenames[1:]),common.IncorrectValue,modname)

    cleantopo = topology.cleanup_topology(topo)
    output = common.open_output_file(outfile)

    for fmt in self.format:
      if fmt == 'nodefault':
        cleantopo.pop('defaults')
      elif fmt == 'noaddr':
        cleantopo.pop('addressing')
      elif fmt in cleantopo:
        cleantopo = cleantopo[fmt]
        break
      else:
        common.error('Invalid format modifier %s' % fmt,common.IncorrectValue,modname)

    common.exit_on_error()
    if modname == 'YAML':
      output.write(cleantopo.to_yaml())
    else:
      output.write(cleantopo.to_json(indent=2,sort_keys=True))
    if outfile != '-':
      common.close_output_file(output)
      print("Created transformed topology dump in YAML format in %s" % outfile)
    else:
      output.write("\n")
