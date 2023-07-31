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

EXTRA_PATH: typing.List[str] = []

def render_from_settings(settings: Box, fmt: str, topo: Box) -> str:
  global EXTRA_PATH
  try:
    return templates.render_template(
      data=topo.to_dict(),
      j2_text = settings[fmt],
      path="reports",
      extra_path=EXTRA_PATH)+"\n"
  except Exception as ex:
    log.fatal(
      text=f"Error rendering topology format {fmt}\n{strings.extra_data_printout(str(ex))}",
      module='report')
    return ""

def render_from_file(fmt: str, topo: Box) -> str:
  global EXTRA_PATH
  try:
    return templates.render_template(
        data=topo.to_dict(),
        j2_file=fmt+".j2",
        path="reports",
        extra_path=EXTRA_PATH)+"\n"
  except jinja2.exceptions.TemplateNotFound:
    log.error(
      text=f'Cannot find "{fmt}.j2" in any of the report directories',
      category=log.IncorrectValue,
      module='report',
      hint='source')
    return ""
  except Exception as ex:
    log.fatal(
      text=f"Error rendering {fmt}\n{strings.extra_data_printout(str(ex))}",
      module="report")
    return ""

def render(fmt: str, settings: Box, topo: Box) -> str:
  return render_from_settings(settings,fmt,topo) if fmt in settings else render_from_file(fmt,topo)

class REPORT(_TopologyOutput):

  DESCRIPTION :str = 'Create a report from the transformed lab topology data'

  def write(self, topo: Box) -> None:
    global EXTRA_PATH
    EXTRA_PATH = _files.get_search_path("reports")
    outfile = self.settings.filename or '-'
    modname = type(self).__name__

    if hasattr(self,'filenames'):
      outfile = self.filenames[0]
      if len(self.filenames) > 1:
        log.error('Extra output filename(s) ignored: %s' % str(self.filenames[1:]),log.IncorrectValue,modname)

    r_collect = ""
    for fmt in self.format:
      r_text = render(fmt,self.settings,topo)
      if '.html' in fmt:
        self.settings.html = r_text
        r_text = render('page.html',self.settings,self.settings)
      r_collect += r_text

    if r_collect:
      _files.create_file_from_text(outfile,r_collect)
