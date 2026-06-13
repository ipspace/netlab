#
# netlab clab build command
#
# Build custom container images
#
import argparse
import os
import pathlib
import tempfile
import typing

from box import Box
from jinja2.exceptions import TemplateError

from ...utils import files as _files
from ...utils import log, strings, templates
from .. import external_commands


def build_parser(parser: argparse.ArgumentParser) -> None:
  parser.add_argument(
    '-l','--list',
    dest='list',
    action='store_true',
    help='List available routing daemons')

  parser.add_argument(
    '-t','--tag',
    dest='tag',
    action='store',
    help='Specify a non-default tag for the container image')

  parser.add_argument(
    '--sw-version',
    dest='sw_version',
    action='store',
    help='Software version for source-build container images (for example, BIRD release for bird.v2_from_src)')

  parser.add_argument(
    dest='image',
    action='store',
    nargs='?',
    help='Routing daemon name')

def get_dockerfiles() -> dict:
  d_path = _files.get_traversable_path('package:daemons')
  d_list = _files.get_globbed_files(d_path,'*/Dockerfile*')

  df_dict: dict = {}

  for d_file in d_list:
    daemon = os.path.basename(os.path.dirname(d_file))
    basename = os.path.basename(d_file).replace('.j2', '')
    if basename == 'Dockerfile':
      df_dict[daemon] = d_file
    else:
      df_dict[daemon + basename[len('Dockerfile'):]] = d_file

  return df_dict

def get_description(dfname: str) -> str:
  try:
    df_lines = pathlib.Path(dfname).read_text(encoding='utf-8').split('\n')
    for line in df_lines:
      if not line.startswith('LABEL'):
        continue
      if not 'description=' in line:
        continue
      line = line.replace('{{ _sw_version }}','configurable')
      return line.split('description=')[1].replace('"','')

  except Exception:
    return '-- failed --'

  return '-- no description --'

def render_j2_dockerfile(
  df_path: str,
  tmp_dir: str,
  defaults: Box,
  sw_version: typing.Optional[str] = None,
) -> str:
  """
  Render Dockerfile.j2 if needed, return path to use for build.

  If the Dockerfile ends with .j2, it's a Jinja2 template and needs to be rendered
  with netlab device defaults before building.
  """
  if not df_path.endswith('.j2'):
    return df_path  # Regular Dockerfile, use as-is

  strings.print_colored_text('[TEMPLATE] ','cyan',None)
  print(f"Rendering Jinja2 template from {os.path.basename(df_path)}")

  template_data: dict = {'defaults': defaults}
  if sw_version:
    template_data['sw_version'] = sw_version

  # Render template (fail() is available as a standard Jinja2 global function)
  try:
    templates.write_template(
      os.path.dirname(df_path),
      os.path.basename(df_path),
      template_data,
      tmp_dir,
      'Dockerfile')
  except (TemplateError, ValueError) as ex:
    log.fatal(
      f'Failed to render Dockerfile template {os.path.basename(df_path)}: {str(ex)}',
      module='build')

  strings.print_colored_text('[RENDERED] ','green',None)
  print("Template rendered to temporary Dockerfile")

  return os.path.join(tmp_dir, 'Dockerfile')

def build_image(
  image: str,
  tag: typing.Optional[str],
  defaults: Box,
  sw_version: typing.Optional[str] = None,
) -> None:
  df_dict = get_dockerfiles()
  if not image in df_dict:
    log.fatal(f'Unknown daemon/image {image}, use "netlab clab build -l" to list available images')

  df_path = df_dict[image]
  device = os.path.basename(os.path.dirname(df_path))
  if sw_version and 'sw_version' not in defaults.daemons[device].clab:
    log.fatal(
      f'--sw-version cannot be used with {image} (defaults.daemons.{device}.clab.sw_version is not defined)',
      module='build')

  resolved_sw_version = sw_version if sw_version else (
    defaults.daemons[device].clab.get('sw_version',None) if image != device else None)

  if not tag:
    tag = f'netlab/{image}:{sw_version}' if sw_version else f'netlab/{image}:latest'

  strings.print_colored_text('[STARTING] ','green',None)
  print(f"Building container image {image} with tag {tag}")
  if resolved_sw_version:
    strings.print_colored_text('[BUILDING] ','green',None)
    print(f"Software version: {resolved_sw_version}")

  strings.print_colored_text('[WORKING]  ','green',None)
  print(f"Trying to remove existing container image {tag}")

  if external_commands.run_command(f'docker image rm {tag}',ignore_errors=True,check_result=False):
    strings.print_colored_text('[REMOVED]  ','green',None)
    print(f"Removed existing image {tag}")
  else:
    strings.print_colored_text('[HICCUP]   ','yellow',None)
    print(f"Cannot remove image {tag}, continuing")

  strings.print_colored_text('[WORKING]  ','green',None)
  print("Prune docker layers and builder cache")
  external_commands.run_command('docker image prune -f',ignore_errors=True)
  external_commands.run_command('docker builder prune -f',ignore_errors=True)

  workdir = os.getcwd()
  print()
  strings.print_colored_text('[WORKING]  ','green',None)
  print(f"Building container image {tag}")

  with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)

    # Render Dockerfile.j2 if needed, otherwise use original path
    dockerfile_to_use = render_j2_dockerfile(df_dict[image], tmp, defaults, sw_version)

    status = external_commands.run_command(
      f'docker build -t {tag} -f {dockerfile_to_use} .',
      ignore_errors=True,
      check_result=False)
    if status:
      strings.print_colored_text('[FINISHED] ','green',None)
      print(f"Container image {tag} for {image} daemon built and installed")
    else:
      strings.print_colored_text('[FAILED]   ','red',None)
      print(f"Failed to build the container image {tag} for {image} daemon")

  os.chdir(workdir)
  print()
  external_commands.run_command(f'docker image ls {tag}',ignore_errors=True)

def list_dockerfiles() -> None:
  rows = []
  df_dict = get_dockerfiles()
  for daemon in sorted(df_dict.keys()):
    # Strip .j2 extension from daemon name if present for display
    display_name = daemon.replace('.j2', '')
    rows.append([display_name, f'netlab/{display_name}:latest', get_description(df_dict[daemon])])

  print("""
The 'netlab clab build' command can be used to build the following container images
""")
  strings.print_table(['daemon','default tag','description'],rows,inter_row_line=False)

def clab_build(args: argparse.Namespace, settings: Box) -> None:
  if args.list:
    list_dockerfiles()
    return

  if args.image:
    build_image(args.image,args.tag,settings,args.sw_version)
    return

  log.fatal('Specify image to build or "--list". Use "--help" to get help')
