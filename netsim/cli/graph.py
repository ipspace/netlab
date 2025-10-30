#
# netlab graph command
#
# Connect a graph description for Graphviz or D2
#
import argparse
import textwrap
import typing
from pathlib import Path

from box import Box

from ..outputs import _TopologyOutput
from ..utils import log, strings
from ..utils import read as _read
from . import external_commands, load_data_source, parser_add_verbose, parser_data_source


#
# CLI parser for 'netlab graph' command
#
def graph_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog="netlab graph",
    description='Create a graph description in Graphviz or D2 format or draw a graph',
    epilog=textwrap.dedent("""
      If you specify an image file as the output file (filename ending in
      png/svg/jpg), netlab graph command tries to run graphviz (dot) or d2 on
      the generated graph description file to create the image file you want.
      """))
  parser.add_argument(
    '-t','--type',
    dest='g_type', action='store',
    choices=['topology','bgp','isis'],
    help='Graph type')
  parser.add_argument(
    '-f','--format',
    dest='g_format', action='store',
    help='Graph formatting parameters separated by commas')
  parser.add_argument(
    '-e','--engine',
    dest='engine', action='store',
    default='graphviz',
    choices=['graphviz','d2'],
    help='Graphing engine')
  parser.add_argument(
    dest='output', action='store',
    nargs='?',
    help='Optional: Output file name')

  parser_add_verbose(parser,verbose=False)
  parser_data_source(parser,t_used=True,action='create a graph from')
  return parser.parse_args(args)

def parse_output(args: argparse.Namespace, topology: Box) -> typing.Tuple[typing.Optional[str],typing.Optional[str]]:
  if not args.output:
    return (None,None)
  o_path = Path(args.output)
  sfx = o_path.suffix[1:]
  if sfx in topology.defaults.netlab.graph.types:
    g_sfx = '.dot' if args.engine == 'graphviz' else '.d2'
    return (sfx,str(o_path.with_suffix(g_sfx)))
  else:
    return (None,args.output)

"""
Execute the graphviz/D2 command to create the final graph
"""
def create_graph(o_type: str, o_name: str, args: argparse.Namespace, topology: Box) -> None:
  g_settings = topology.defaults.outputs['graph' if args.engine == 'graphviz' else 'd2']
  if 'command' not in g_settings:                 # Do we know what command to execute?
    log.warning(
      text=f"Don't know how to create a {args.engine} graph, you'll have to do it yourself",
      module='graph')
    return
  cmd = g_settings.command                        # Get the command (template) to execute
  c_exec = cmd.split(' ')[0]                      # Get the program name
  if not external_commands.run_command(f'which {c_exec}',check_result=True,ignore_errors=True):
    log.warning(
      text=f"Cannot find the {c_exec} command. You will have to install additional software",
      more_hints="You could use 'netlab install graph' on Ubuntu to install graphviz and D2",
      module='graph')                             # Looks like we can't find the program we need
    return

  o_stem = Path(o_name).with_suffix('')
  cmd = strings.eval_format(cmd,{'gfile': o_name, 'gtype': o_type, 'gname': o_stem})
  if external_commands.run_command(cmd,ignore_errors=True):
    log.info(text=f'Created {o_stem}.{o_type} from {o_name}')

def run(cli_args: typing.List[str]) -> None:
  args = graph_parse(cli_args)
  topology = load_data_source(args,ghosts=False)
  _read.include_environment_defaults(topology)
  o_module = 'graph' if args.engine == 'graphviz' else 'd2'
  o_param  = f'{o_module}:{args.g_type or "topology"}'
  (o_type,o_name) = parse_output(args,topology)
  if args.g_format:
    o_param += ':'+args.g_format.replace(',',':')
  if o_name:
    o_param += f'={o_name}'

  graph_module = _TopologyOutput.load(o_param,topology.defaults.outputs[o_module])
  if graph_module:
    graph_module.write(topology)
  else:
    log.fatal('Cannot load the graphing output module, aborting')

  if o_type and o_name:
    create_graph(o_type,o_name,args,topology)