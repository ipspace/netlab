#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import typing
import argparse
import os
import glob

from . import common_parse_args
from . import ansible
from .. import common

#
# CLI parser for 'netlab config' command
#
def custom_config_parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace, typing.List[str]]:
  parser = argparse.ArgumentParser(
    prog='netlab config',
    description='Deploy custom configuration template',
    epilog='All other arguments are passed directly to ansible-playbook')
  parser.add_argument(
    '-v','--verbose',
    dest='verbose',
    action='store_true',
    help='Verbose logging')
  parser.add_argument(
    dest='template', action='store',
    help='Configuration template (or a family of templates)')

  return parser.parse_known_args(args)

def run(cli_args: typing.List[str]) -> None:
  (args,rest) = custom_config_parse(cli_args)

  if args.verbose:
    rest = ['-v'] + rest

  if args.template != '-':
    if os.path.exists(args.template) or \
       os.path.exists(args.template+'.j2') or \
       glob.glob(args.template+'.*.j2'):
      rest = ['-e','config='+args.template] + rest
    else:
      common.fatal('Cannot find specified Jinja2 template: %s' % args.template,'config')

  if args.verbose:
    print('Ansible playbook args: %s' % rest)
  ansible.playbook('config.ansible',rest)
