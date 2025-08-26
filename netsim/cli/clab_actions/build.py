#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import argparse
import os
import pathlib
import tempfile
import typing

from box import Box

from ...utils import files as _files
from ...utils import log, strings
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
    root, ext = os.path.splitext(d_file)
    df_dict[daemon+ext] = d_file

  return df_dict

def get_description(dfname: str) -> str:
  try:
    df_lines = pathlib.Path(dfname).read_text().split('\n')
    for line in df_lines:
      if not line.startswith('LABEL'):
        continue

      if not 'description=' in line:
        continue

      return line.split('description=')[1].replace('"','')
    
  except:
    return '-- failed --'
  
  return '???'

def build_image(image: str, tag: typing.Optional[str]) -> None:
  if tag is None or not tag:
    tag = f'netlab/{image}:latest'

  df_dict = get_dockerfiles()
  if not image in df_dict:
    log.fatal(f'Unknown daemon/image {image}, use "netlab clab build -l" to list available images')

  strings.print_colored_text('[STARTING] ','green',None)
  print(f"Building container image {image} with tag {tag}")

  strings.print_colored_text('[WORKING]  ','green',None)
  print(f"Trying to remove existing container image {tag}")

  if external_commands.run_command(f'docker image rm {tag}',ignore_errors=True,check_result=False):
    strings.print_colored_text('[REMOVED]  ','green',None)
    print(f"Removed existing image {tag}")
  else:
    strings.print_colored_text('[HICCUP]   ','yellow',None)
    print(f"Cannot remove image {tag}, continuing")

  workdir = os.getcwd()
  print()
  strings.print_colored_text('[WORKING]  ','green',None)
  print(f"Building container image {tag}")

  with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)
    status = external_commands.run_command(
      f'docker build -t {tag} -f {df_dict[image]} .',
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
    rows.append([daemon, f'netlab/{daemon}:latest', get_description(df_dict[daemon])])

  print("""
The 'netlab clab build' command can be used to build the following container images
""")
  strings.print_table(['daemon','default tag','description'],rows,inter_row_line=False)

def clab_build(args: argparse.Namespace, settings: Box) -> None:
  if args.list:
    list_dockerfiles()
    return
  
  if args.image:
    build_image(args.image,args.tag)
    return
  
  log.fatal('Specify image to build or "--list". Use "--help" to get help')
