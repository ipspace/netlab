#
# netlab down command
#
# * Transform lab topology or read transformed lab topology from snapshot file
# * Stop the lab, including provider-specific pre- and post-stop hooks
# * Clean up the working directory (optional)
#
import argparse
import typing
import textwrap
from box import Box

from . import common_parse_args, topology_parse_args, load_topology, load_snapshot_or_topology, external_commands,fs_cleanup
from .. import read_topology,augment,common
from .. import providers
from .up import provider_probes
#
# CLI parser for 'netlab down' command
#
def down_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    parents=[ topology_parse_args() ],
    prog="netlab down",
    description='Destroy the virtual lab')

  parser.add_argument(
    '-v','--verbose',
    dest='verbose',
    action='count',
    default = 0,
    help='Verbose logging (where applicable)')
  parser.add_argument(
    '--cleanup',
    dest='cleanup',
    action='store_true',
    help='Remove all configuration files created by netlab create')
  parser.add_argument(
    '--snapshot',
    dest='snapshot',
    action='store',
    nargs='?',
    const='netlab.snapshot.yml',
    help='Transformed topology snapshot file')
  parser.add_argument(
    dest='topology', action='store', nargs='?',
    help='Topology file (default: topology.yml)')

  return parser.parse_args(args)

def down_cleanup(topology: Box, verbose: bool = False) -> None:
  p_provider = topology.provider
  cleanup_list = topology.defaults.providers[p_provider].cleanup or []

  for s_provider in topology[p_provider].providers:
    cleanup_list.extend(topology.defaults.providers[s_provider].cleanup or [])
    s_filename = topology.defaults.providers[p_provider][s_provider].filename
    if s_filename:
      cleanup_list.append(s_filename)

  cleanup_list.extend(topology.defaults.automation.ansible.cleanup)
  cleanup_list.append('netlab.snapshot.yml')
  fs_cleanup(cleanup_list,verbose)

def stop_provider_lab(topology: Box, pname: str, sname: typing.Optional[str] = None) -> None:
  p_name = sname or pname
  p_topology = providers.select_topology(topology,p_name)
  p_module   = providers._Provider.load(p_name,topology.defaults.providers[p_name])

  exec_command = None
  if sname is not None:
    exec_command = topology.defaults.providers[pname][sname].stop

  p_module.call('pre_stop_lab',p_topology)
  external_commands.stop_lab(topology.defaults,p_name,2,"netlab down",exec_command)
  p_module.call('post_stop_lab',p_topology)

def run(cli_args: typing.List[str]) -> None:
  args = down_parse(cli_args)
  topology = load_snapshot_or_topology(args)

  if args.topology:
    print(f"Reading lab topology from {args.topology}")
  else:
    print(f"Reading transformed lab topology from snapshot file {args.snapshot}")

  if topology is None:
    common.fatal('... could not read the lab topology, aborting')
    return

  provider_probes(topology)

  p_provider = topology.provider
  p_module = providers._Provider.load(p_provider,topology.defaults.providers[p_provider])
  providers.mark_providers(topology)
  p_module.call('pre_output_transform',topology)

  for s_provider in topology[p_provider].providers:
    stop_provider_lab(topology,p_provider,s_provider)
    print()

  stop_provider_lab(topology,p_provider)

  if args.cleanup:
    external_commands.print_step(3,"Cleanup configuration files",spacing = True)
    down_cleanup(topology,True)
