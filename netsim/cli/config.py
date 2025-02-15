#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import typing
import argparse
import os
import glob
from box import Box

from . import parser_add_verbose,parser_lab_location,load_snapshot
from .external_commands import set_ansible_flags
from . import ansible
from ..utils import log

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

def template_sanity_check(template: str, topology: Box, verbose: bool) -> bool:
  for path in topology.defaults.paths.custom.dirs:
    c_path = path+"/"+template
    if verbose:
      print(f"Looking for {c_path}")
    if os.path.isdir(c_path) or \
       os.path.exists(c_path+'.j2') or \
       glob.glob(c_path+'.*.j2'):
      return True

  return False

def run(cli_args: typing.List[str]) -> None:
  (args,rest) = custom_config_parse(cli_args)
  log.set_logging_flags(args)
  set_ansible_flags(rest)

  topology = load_snapshot(args)

  if args.template != '-':
    if template_sanity_check(args.template,topology,args.verbose):
      rest = ['-e','config='+args.template] + rest
    else:
      log.fatal(f'Cannot find specified Jinja2 template or configuration directory { args.template }','config')

  if args.verbose:
    print(f'Ansible playbook args: { rest }')
  if args.reload:
    ansible.playbook('reload-config.ansible',rest)
  else:
    ansible.playbook('config.ansible',rest)

  log.repeat_warnings('netlab initial')
