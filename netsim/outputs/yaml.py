#
# Create YAML or JSON output
#
import typing

import yaml
import os
from box import Box,BoxList

from .. import data
from ..augment import topology
from ..utils import files as _files
from ..utils import log,strings

from . import _TopologyOutput,check_writeable

class YAML(_TopologyOutput):

  DESCRIPTION :str = 'Inspect transformed data in YAML format'

  def write(self, topo: Box) -> None:
    outfile = self.settings.filename or '-'
    modname = type(self).__name__

    if hasattr(self,'filenames'):
      outfile = self.filenames[0]
      if len(self.filenames) > 1:
        log.error('Extra output filename(s) ignored: %s' % str(self.filenames[1:]),log.IncorrectValue,modname)

    if outfile == 'netlab.snapshot.yml':
      check_writeable('netlab.snapshot.yml')

    cleantopo: typing.Any = topology.cleanup_topology(topo)
    output = _files.open_output_file(outfile)

    for fmt in self.format:
      if fmt == 'nodefault':
        cleantopo.pop('defaults')
      elif fmt == 'noaddr':
        cleantopo.pop('addressing')
      else:
        try:
          result = eval(fmt,cleantopo) if fmt != '.' else cleantopo
        except Exception as ex:
          log.fatal(f'Error trying to evaluate {fmt}: {str(ex)}')
          return
        cleantopo = result
        break

    if not isinstance(cleantopo,Box) and not isinstance(cleantopo,BoxList):
      output.write(f"{str(result)}\n")
    elif modname == 'YAML':
      output.write(strings.get_yaml_string(cleantopo))
    else:
      output.write(cleantopo.to_json(indent=2,sort_keys=True))

    if outfile != '-':
      _files.close_output_file(output)
      print(f"Created transformed topology dump in {modname} format in {outfile}")
    else:
      output.write("\n")
