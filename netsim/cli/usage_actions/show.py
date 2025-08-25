import argparse

from box import Box

from ...data import get_empty_box
from ...utils import read as _read
from ...utils import stats, strings
from .. import parser_subcommands


def format_parser(parser: argparse.ArgumentParser) -> None:
  parser.add_argument(
    '--format',
    dest='format',
    action='store',
    choices=['table','yaml'],
    default='table',
    help='Output format (table, text, yaml)')

def remove_blanks(data: Box) -> None:
  for k in list(data.keys()):
    if data[k] == '':
      data.pop(k,None)
    elif isinstance(data[k],Box):
      remove_blanks(data[k])

def display_results(data: Box, header: dict, args: argparse.Namespace, underscore_is_dot: bool = False) -> None:
  if args.format == 'yaml':
    remove_blanks(data)
    print(data.to_yaml())
    return
  
  t_header: list = list(header.values())
  rows: list = []

  for k,v in data.items():
    row: list = []
    for item in header.keys():
      if item == 'key':
        if underscore_is_dot:
          k = k.replace('_','.')
        row.append(k)
      else:
        cell = v[item] if item in v else ""
        row.append(str(cell).rjust(len(header[item])) if isinstance(cell,int) else str(cell))

    rows.append(row)

  strings.print_table(t_header,rows)

def show_commands(args: argparse.Namespace) -> None:
  d_stat = stats.read_stats()
  t_header = {
    'key': 'command',
    'cnt': 'Total',
    'avg_cnt': 'Daily average',
    'fail': 'Failed (total)',
    'avg_fail': 'Failed (average)'}

  result = get_empty_box()
  for cmd in sorted(d_stat.cli.keys()):
    cdata = d_stat.cli[cmd]
    result[cmd].cnt = cdata.start.cnt or ""
    result[cmd].avg_cnt = cdata.start.avg_cnt or ""
    if cmd != 'usage' and 'done' in cdata:
      result[cmd].fail = max((cdata.start.cnt or 0) - (cdata.done.cnt or 0),0) or ""
      result[cmd].avg_fail = max((cdata.start.avg_cnt or 0) - (cdata.done.avg_cnt or 0),0) or ""

  display_results(result,t_header,args)

def show_modules(args: argparse.Namespace) -> None:
  d_stat = stats.read_stats()
  t_header = {
    'key': 'Module',
    'cnt': 'Used',
    'pct': '% use' }

  m_max = d_stat.cli.up.start.cnt or 0

  result = get_empty_box()
  for m_name in sorted(d_stat.module.keys()):
    m_data = d_stat.module[m_name]
    result[m_name].cnt = m_data.use.cnt or 0

  m_max = max([ m_data.cnt for m_data in result.values() ] + [ m_max ])
  for m_data in result.values():
    m_data.pct = f'{100 * m_data.cnt/m_max:5.2f}'

  display_results(result,t_header,args)

def show_plugins(args: argparse.Namespace) -> None:
  d_stat = stats.read_stats()
  t_header = {
    'key': 'Plugin',
    'cnt': 'Used',
    'pct': '% use' }

  m_max = d_stat.cli.up.start.cnt or 0

  result = get_empty_box()
  for m_name in sorted(d_stat.plugin.keys()):
    m_data = d_stat.plugin[m_name]
    result[m_name].cnt = m_data.use.cnt or 0

  m_max = max([ m_data.cnt for m_data in result.values() ] + [ m_max ])
  for m_data in result.values():
    m_data.pct = f'{100 * m_data.cnt/m_max:5.2f}'

  display_results(result,t_header,args,underscore_is_dot=True)

def show_devices(args: argparse.Namespace) -> None:
  d_stat = stats.read_stats()
  topology = _read.load("package:cli/empty.yml")
  t_header = { 'key': 'device', 'total': 'Total' }
  p_list = sorted(topology.defaults.providers.keys())
  for p_name in p_list:
    t_header[p_name] = p_name
  result = get_empty_box()
  for d_name in sorted(d_stat.device.keys()):
    d_data = d_stat.device[d_name]
    result[d_name].total = d_data.use.cnt
    for p_name in p_list:
      result[d_name][p_name] = d_data.provider[p_name].cnt if p_name in d_data.provider else ''

  display_results(result,t_header,args)

show_dispatch: dict = {
  'commands': {
    'exec':  show_commands,
    'parser': format_parser,
    'description': 'show netlab command usage'
  },
  'devices': {
    'exec':  show_devices,
    'parser': format_parser,
    'description': 'show devices used in lab topologies'
  },
  'modules': {
    'exec':  show_modules,
    'parser': format_parser,
    'description': 'show modules used in lab topologies'
  },
  'plugins': {
    'exec':  show_plugins,
    'parser': format_parser,
    'description': 'show plugins used in lab topologies'
  }
}

def show_parser(parser: argparse.ArgumentParser) -> None:
  global show_dispatch
  parser_subcommands(parser,show_dispatch)
