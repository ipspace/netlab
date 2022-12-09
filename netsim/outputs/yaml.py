#
# Create YAML or JSON output
#
import typing

import yaml
import os
from box import Box,BoxList

from .. import common
from .. import data
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

    cleantopo: typing.Any = topology.cleanup_topology(topo)
    output = common.open_output_file(outfile)

    for fmt in self.format:
      if fmt == 'nodefault':
        cleantopo.pop('defaults')
      elif fmt == 'noaddr':
        cleantopo.pop('addressing')
      elif data.get_from_box(cleantopo,fmt):
        result = data.get_from_box(cleantopo,fmt)
        if not isinstance(result,Box) and not isinstance(result,BoxList):
          common.fatal(f'Selecting {fmt} did not result in a usable dictionary, aborting')
          return
        cleantopo = result
        break
      else:
        common.error('Invalid format modifier %s' % fmt,common.IncorrectValue,modname)

    common.exit_on_error()
    if modname == 'YAML':
      output.write(common.get_yaml_string(cleantopo))
    else:
      output.write(cleantopo.to_json(indent=2,sort_keys=True))
    if outfile != '-':
      common.close_output_file(output)
      print("Created transformed topology dump in YAML format in %s" % outfile)
    else:
      output.write("\n")
