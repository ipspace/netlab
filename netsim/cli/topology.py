#
# netsim-tools CLI parsers
#
# Contain parsers for create-topology script and the main netlab CLI
#
import argparse
import typing
from .. import common,read_topology,augment

from ..outputs import ansible
from ..providers import _Provider

#
# CLI parser for create-topology script
#
def create_topology_parse(args: typing.Optional[typing.List[str]] = None) -> argparse.Namespace:
  parser = argparse.ArgumentParser(description='Create topology data from topology description')
  parser.add_argument('-t','--topology', dest='topology', action='store', default='topology.yml',
                  help='Topology file')
  parser.add_argument('--defaults', dest='defaults', action='store', default='topology-defaults.yml',
                  help='Local topology defaults file')
  parser.add_argument('-x','--expanded', dest='xpand', action='store', nargs='?', const='topology-expanded.yml',
                  help='Create expanded topology file')
  parser.add_argument('-p','-g','--vagrantfile', dest='provider', action='store', nargs='?', const='',
                  help='Create provider-specific configuration file (default: Vagrantfile)')
  parser.add_argument('-i','--inventory', dest='inventory', action='store', nargs='?', const='hosts.yml',
                  help='Create Ansible inventory file, default hosts.yml')
  parser.add_argument('-c','--config', dest='config', action='store', nargs='?', const='ansible.cfg',
                  help='Create Ansible configuration file, default ansible.cfg')
  parser.add_argument('--hostvars', dest='hostvars', action='store', default='dirs',
                  choices=['min','files','dirs'],
                  help='Ansible hostvars format')
  parser.add_argument('--log', dest='logging', action='store_true',
                  help='Enable basic logging')
  parser.add_argument('-q','--quiet', dest='quiet', action='store_true',
                  help='Report only major errors')
  parser.add_argument('-v','--view', dest='verbose', action='store_true',
                  help='Display data instead of creating a file')
  return parser.parse_args(args)

#
# Moved old main routine from __init__.py
#

def legacy_main(args: argparse.Namespace) -> None:
  common.set_logging_flags(args)
  topology = read_topology.load(args.topology,args.defaults,"package:topology-defaults.yml")
  common.exit_on_error()

  augment.main.transform(topology)
  common.exit_on_error()
  if args.provider is not None:
    provider = _Provider.load(topology.provider,topology.defaults.providers[topology.provider])
    if args.verbose:
      common.error("Use 'netlab create -o provider=-' to write provider configuration file to stdout")
    else:
      provider.create(topology,args.provider)

  if args.xpand:
    augment.topology.create_topology_file(topology,args.xpand)

  if args.inventory:
    if args.verbose:
      ansible.dump(topology)
    else:
      ansible.ansible_inventory(topology,args.inventory,args.hostvars)

  if args.config:
    ansible.ansible_config(args.config,args.inventory)

def run(cli_args: typing.List[str]) -> None:
  legacy_main(create_topology_parse(cli_args))
