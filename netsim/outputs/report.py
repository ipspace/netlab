#
# Create YAML or JSON output
#
import typing
import pathlib

from box import Box
import jinja2

from .. import data
from ..augment import topology
from ..utils import files as _files
from ..utils import log,templates,strings

from . import _TopologyOutput

class REPORT(_TopologyOutput):

  def write(self, topo: Box) -> None:
    outfile = self.settings.filename or '-'
    modname = type(self).__name__

    if hasattr(self,'filenames'):
      outfile = self.filenames[0]
      if len(self.filenames) > 1:
        log.error('Extra output filename(s) ignored: %s' % str(self.filenames[1:]),log.IncorrectValue,modname)

    output = _files.open_output_file(outfile)

    extra_path = _files.get_search_path("reports")
    for fmt in self.format:
      if fmt in self.settings:
        try:
          output.write(
            templates.render_template(
              data=topo.to_dict(),
              j2_text = self.settings[fmt],
              path="reports",
              extra_path=extra_path)+"\n")
          output.write("\n")
        except Exception as ex:
          log.error(
            text=f"Error rendering topology format {fmt}\n{strings.extra_data_printout(str(ex))}",
            category=log.IncorrectValue)
        continue

      try:
        output.write(
          templates.render_template(
            data=topo.to_dict(),
            j2_file=fmt+".j2",
            path="reports",
            extra_path=extra_path)+"\n")
      except jinja2.exceptions.TemplateNotFound:
        log.error(
          text=f'Cannot find "{fmt}" in any of the report directories',
          category=log.IncorrectValue,
          module='report',
          hint='source')
      except Exception as ex:
        log.error(
          text=f"Error rendering {fmt}\n{strings.extra_data_printout(str(ex))}",
          category=log.IncorrectValue)
