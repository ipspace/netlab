#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import typing
import argparse
import os
import glob

from . import parser_add_verbose
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

  return parser.parse_known_args(args)

def run(cli_args: typing.List[str]) -> None:
  (args,rest) = custom_config_parse(cli_args)
  log.set_logging_flags(args)
  set_ansible_flags(rest)

  if args.template != '-':
    if os.path.exists(args.template) or \
       os.path.exists(args.template+'.j2') or \
       glob.glob(args.template+'.*.j2'):
      rest = ['-e','config='+args.template] + rest
    else:
      log.fatal(f'Cannot find specified Jinja2 template or configuration directory { args.template }','config')

  if args.verbose:
    print(f'Ansible playbook args: { rest }')
  if args.reload:
    ansible.playbook('reload-config.ansible',rest)
  else:
    ansible.playbook('config.ansible',rest)
