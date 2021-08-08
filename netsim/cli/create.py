#
# netlab create command
#
# Creates virtualization provider configuration and automation inventory from
# the specified topology
#
import argparse
import typing

from . import common_parse_args, topology_parse_args
from .. import set_logging_flags
from .. import read_topology,inventory,augment,common
from ..providers import Provider

#
# CLI parser for create-topology script
#
def create_topology_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    parents=[ common_parse_args(), topology_parse_args() ],
    prog="netlab create",
    description='Create provider- and automation configuration files')

  parser.add_argument(
    dest='topology', action='store', nargs='?',
    type=argparse.FileType('r'),
    default='topology.yml',
    help='Topology file (default: topology.yml)')
  parser.add_argument(
    '-i','--inventory',
    dest='inventory',
    action='store',
    help='Automation inventory file name (default: hosts.yml)')
  parser.add_argument('-c','--config',dest='config', action='store', help='Automation configuration file (default: ansible.cfg)')
  parser.add_argument('-g',dest='vagrantfile', action='store',help='Virtualization provider configuration file name')
  parser.add_argument('--hostvars', dest='hostvars', action='store', default='dirs',
                  choices=['min','files','dirs'],
                  help='Ansible hostvars format')
  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  args = create_topology_parse(cli_args)
  set_logging_flags(args)
  topology = read_topology.load(args.topology.name,args.defaults,"package:topology-defaults.yml")
  read_topology.add_cli_args(topology,args)
  common.exit_on_error()

  augment.main.transform(topology)
  common.exit_on_error()

  # Create provider configuration file
  #
  provider = Provider.load(topology.provider,topology.defaults.providers[topology.provider])
  provider.create(topology,args.vagrantfile)

  inventory.write(data=topology,fname=args.inventory)
  inventory.config(args.config,args.inventory)
