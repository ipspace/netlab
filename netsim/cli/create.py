#
# netlab create command
#
# Creates virtualization provider configuration and automation inventory from
# the specified topology
#
import argparse
import typing
import textwrap
import os
import sys
from box import Box

from . import common_parse_args, topology_parse_args, load_topology
from .. import augment
from ..utils import log, read as _read,strings
from ..outputs import _TopologyOutput

#
# CLI parser for create-topology script
#
def create_topology_parse(
      args: typing.List[str],
      cmd: str,
      description: str,
      extra_args: typing.Optional[argparse.ArgumentParser]) -> argparse.Namespace:
  if cmd != 'create':
    epilog = ""
  else:
    epilog = textwrap.dedent('''
      output files created when no output is specified:

        * Transformed topology snapshot in netlab.snapshot.yml
        * Virtualization provider file with provider-specific filename
          (Vagrantfile or clab.yml)
        * Ansible inventory file (hosts.yml) and configuration (ansible.cfg)

      For a complete list of output formats please consult the documentation
    ''')
  parents = [ common_parse_args(True), topology_parse_args() ]
  if extra_args:
    parents.append(extra_args)
  parser = argparse.ArgumentParser(
    parents=parents,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    prog=f"netlab {cmd}",
    description=description,
    epilog=epilog)
  parser.add_argument('--unlock', dest='unlock', action='store_true',
                  help=argparse.SUPPRESS)

  parser.add_argument(
    dest='topology', action='store', nargs='?',
    type=argparse.FileType('r'),
    default='topology.yml',
    help='Topology file (default: topology.yml)')

  if cmd == 'create':
    parser.add_argument('-o','--output',dest='output', action='append',help='Output format(s): format:option=filename')
    parser.add_argument('--devices',dest='devices', action='store_true',help='Create provider configuration file and netlab-devices.yml')

  return parser.parse_args(args)

def run(cli_args: typing.List[str],
        cli_command: str = 'create',
        cli_describe: str = 'Create provider- and automation configuration files',
        cli_extra_args: typing.Optional[argparse.ArgumentParser] = None ) -> Box:
  args = create_topology_parse(cli_args, cli_command, cli_describe, cli_extra_args)
  if not 'output' in args:
    args.output = None
  if not 'devices' in args:
    args.devices = None

  if not args.output:
    args.output = ['provider','yaml=netlab.snapshot.yml','tools']
    args.output.append('devices' if args.devices else 'ansible:dirs')
  elif args.devices:
    log.error('--output and --devices flags are mutually exclusive',log.IncorrectValue,'create')

  topology = load_topology(args)
  augment.main.transform(topology)
  log.exit_on_error()

  if args.unlock and os.path.exists('netlab.lock'):
    strings.print_colored_text("WARNING: ","bright_red",stderr=True)
    print("removing netlab.lock file, you're on your own",file=sys.stderr)
    os.remove('netlab.lock')

  for output_format in args.output:
    output_module = _TopologyOutput.load(output_format,topology.defaults.outputs[output_format.split(':')[0]])
    if output_module:
      output_module.write(topology)
    else:
      log.error('Unknown output format %s' % output_format,log.IncorrectValue,'create')

  return topology
