#
# netlab create command
#
# Creates virtualization provider configuration and automation inventory from
# the specified topology
#
import argparse
import os
import sys
import textwrap
import typing
from pathlib import Path

import requests
from box import Box

from .. import augment
from ..outputs import _TopologyOutput
from ..utils import log, strings
from . import common_parse_args, error_and_exit, lab_status_log, load_topology, topology_parse_args


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

        * Pickled transformed data in netlab.snapshot.pickle
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
    default='topology.yml',
    help='Topology file or URL (default: topology.yml)')

  if cmd == 'create':
    parser.add_argument('-o','--output',dest='output', action='append',help='Output format(s): format:option=filename')
    parser.add_argument('--devices',dest='devices', action='store_true',help='Create provider configuration file and netlab-devices.yml')

  return parser.parse_args(args)

"""
Fix URLs to YAML files hosted on public Git repositories. Currently, only Github is supported
"""
def fix_git_repo_url(url: str) -> str:
  if 'github.com' in url and '?' not in url:
    return url + '?raw=true'
  
  return url

"""
Fetch topology from the specified URL, store it in 'downloaded.yml' file in
current directory, warn if the directory is not empty
"""
def http_fetch_content(url: str, args: typing.Union[argparse.Namespace,Box]) -> str:
  fname = 'downloaded.yml'
  url = fix_git_repo_url(url)
  try:
    c = requests.get(url)
    Path(fname).write_text(c.text)
    try:
      Box().from_yaml(yaml_string=c.text)
    except Exception as ex:
      error_and_exit(
        f'The content downloaded from {url} is not valid YAML',
        module='http',
        category=log.FatalError,
        more_hints=[ str(ex), f'The content has been saved in {fname} where you can inspect it' ])
  except Exception as ex:
    error_and_exit(
      f'Cannot download the lab topology from {url}',
      module='http',
      category=log.FatalError,
      more_hints=f'{str(ex)}')

  if args.quiet:
    return fname

  log.info(f'Downloaded the lab topology into {fname}')
  for d_file in Path('.').glob('*'):
    if d_file != fname:
      log.info('The "netlab up" or "netlab create" command with a URL should be executed in an empty directory')
      if not strings.confirm('\nThe current directory is not empty. Do you want to continue'):
        error_and_exit('User decided to abort the request')
      break

  return fname

def run(cli_args: typing.List[str],
        cli_command: str = 'create',
        cli_describe: str = 'Create provider- and automation configuration files',
        cli_extra_args: typing.Optional[argparse.ArgumentParser] = None ) -> Box:
  args = create_topology_parse(cli_args, cli_command, cli_describe, cli_extra_args)
  if not 'output' in args:
    args.output = None
  if not 'devices' in args:
    args.devices = None

  if '://' in args.topology:
    args.topology = http_fetch_content(args.topology,args)

  if not args.output:
    args.output = ['provider','yaml=netlab.snapshot.yml','pickle','tools']
    args.output.append('devices' if args.devices else 'ansible:dirs')
  elif args.devices:
    log.error('--output and --devices flags are mutually exclusive',log.IncorrectValue,'create')

  tpath = Path(args.topology)
  if not tpath.exists():
    log.fatal(f'Topology file {args.topology} does not exist',module='create')
  if not tpath.is_file():
    log.fatal(f'The specified lab topology ({args.topology}) is not a file',module='create')

  topology = load_topology(args)
  augment.main.transform(topology)
  log.exit_on_error()

  if args.unlock and os.path.exists('netlab.lock'):
    strings.print_colored_text("WARNING: ","bright_red",stderr=True)
    print("removing netlab.lock file, you're on your own",file=sys.stderr)
    os.remove('netlab.lock')
    lab_status_log(topology,'Configuration files have been recreated')

  # Iterate over plugins that registered 'output' hook
  # We have to reload the plugin as the original 'Plugin' dictionary was removed
  # as the last step in the topology transformation process
  #
  for p_name in topology.defaults.netlab.create.get('output',[]):
    plugin = augment.plugin.load_plugin(p_name,topology)
    if plugin:
      augment.plugin.execute_plugin_hook('output',plugin,topology)

  for output_format in args.output:
    output_module = _TopologyOutput.load(output_format,topology.defaults.outputs[output_format.split(':')[0]])
    if output_module:
      output_module.write(topology)
      log.exit_on_error()
    else:
      log.error('Unknown output format %s' % output_format,log.IncorrectValue,'create')

  return topology
