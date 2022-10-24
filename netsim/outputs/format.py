#
# Create YAML or JSON output
#
import typing

import yaml
import os
from box import Box,BoxList
from jinja2 import Environment, BaseLoader, FileSystemLoader, StrictUndefined, make_logging_undefined

from .. import common
from .. import data
from ..augment import topology

from . import _TopologyOutput

class FORMAT(_TopologyOutput):

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
      if not fmt in self.settings:
        common.error(f'Unknown template format {fmt}',common.IncorrectValue,modname)
        print(topo.defaults.outputs.format)
        continue

      template = Environment(loader=BaseLoader(), \
              trim_blocks=True,lstrip_blocks=True, \
              undefined=make_logging_undefined(base=StrictUndefined)).from_string(self.settings[fmt])
      output.write(template.render(**topo))
      output.write("\n")
