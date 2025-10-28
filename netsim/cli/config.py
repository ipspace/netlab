#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import argparse
import glob
import os
import typing

from box import Box

from ..utils import files as _files
from ..utils import log
from . import ansible, load_snapshot, parser_add_verbose, parser_lab_location
from .external_commands import set_ansible_flags


#
# CLI parser for 'netlab config' command
#
def custom_config_parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace, typing.List[str]]:
  parser = argparse.ArgumentParser(
    prog='netlab config',
    description='Deploy custom configuration template',
    epilog='All other arguments are passed directly to ansible-playbook')
  parser.add_argument(
    '-r','--reload',
    dest='reload',
    action='store_true',
    help='Reload saved device configurations')
  parser.add_argument(
    dest='template', action='store',
    help='Configuration template or a directory with templates')
  parser_add_verbose(parser)
  parser_lab_location(parser,instance=True,action='configure')

  return parser.parse_known_args(args)

def path_exists(c_path: str) -> bool:
  return bool(
      os.path.isdir(c_path) or
      os.path.exists(c_path+'.j2') or
      glob.glob(c_path+'.*.j2'))

def template_sanity_check(template: str, topology: Box, verbose: bool) -> bool:
  if template.startswith("/"):                    # Absolute path specified as the template name?
    return path_exists(template)

  for path in topology.defaults.paths.custom.dirs:
    c_path = path+"/"+template
    if verbose:
      print(f"Looking for {c_path}")
    if path_exists(c_path):
      return True

  return False

def run(cli_args: typing.List[str]) -> None:
  (args,rest) = custom_config_parse(cli_args)
  log.set_logging_flags(args)
  set_ansible_flags(rest)

  topology = load_snapshot(args)

  if args.template != '-':
    if args.template[0] in "~/.":                 # Change directory references into absolute path
      args.template = str(_files.absolute_path(args.template))

    if template_sanity_check(args.template,topology,args.verbose):
      rest = ['-e','config='+args.template] + rest
    else:
      log.fatal(f'Cannot find specified Jinja2 template or configuration directory { args.template }','config')

  ansible.check_version()
  if args.verbose:
    print(f'Ansible playbook args: { rest }')
  if args.reload:
    ansible.playbook('reload-config.ansible',rest)
  else:
    ansible.playbook('config.ansible',rest)

  log.repeat_warnings('netlab initial')
