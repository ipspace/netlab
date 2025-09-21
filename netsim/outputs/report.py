#
# Create YAML or JSON output
#
import typing

import jinja2
from box import Box
from rich.console import Console
from rich.markdown import Markdown

from ..utils import files as _files
from ..utils import log, strings, templates
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
    outfile = self.select_output_file('-')
    if outfile is None:
      return

    r_collect = ""
    for fmt in self.format:
      ascii = fmt.endswith('.ascii')
      if ascii:
        fmt = fmt.replace('.ascii','.md')
        console = Console() if outfile != '-' else strings.rich_console

      r_text = render(fmt,self.settings,topo)
      if '.html' in fmt:
        self.settings.html = r_text
        r_text = render('page.html',self.settings,self.settings)
      if ascii:
        r_text = r_text.replace('<br />','').replace('<br/>','').replace('<br>','')
        md_text = Markdown(r_text)
        with console.capture() as capture:
          console.print(md_text)

        r_text = capture.get()

      r_collect += r_text

    if r_collect:
      _files.create_file_from_text(outfile,r_collect)
