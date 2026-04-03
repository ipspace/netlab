#
# netlab show providers command -- display virtualization providers
#

import argparse

from box import Box

from ... import data
from ...utils import log, strings
from ..external_commands import test_probe
from . import show_common_parser


def parse() -> argparse.ArgumentParser:
  parser = show_common_parser('providers','supported virtualization providers')
  parser.add_argument(
    '-p','--provider',
    dest='provider',
    action='store',
    help='Display the status of the selected virtualization provider')

  return parser

def get_provider_status(settings: Box, pname: str, quiet: bool) -> str:
  OK_count = 0
  probes = settings.providers[pname].probe                  # Get the provider probes
  if not probes:                                            # ... nothing to check, assume it's OK
    return "OK"
  
  if not isinstance(probes,list):                           # Turn probes into a list (just in case)
    probes = [ probes ]

  for p in probes:                                          # Iterate over probes
    if not quiet:                                           # If we want printouts, we have to do some extra work
      if isinstance(p,Box):                                 # If a probe is specified as a cmd/err, try to generate useful errors
        pcmd = str(p.cmd)                                   # ... first, select the command to print out
        if isinstance(p.cmd,str):                           # ... and then turn the probe into a string if you can
          p = p.cmd
      else:
        pcmd = str(p)                                       # anything else, just stringify the command to print

      print(f"Executing: {pcmd}")

    if test_probe(p,quiet):                                 # Did the probe succeed?
      OK_count += 1                                         # ... remember at least one probe succeeded
    else:
      return "FAIL" if OK_count else "N/A"                  # Probe failed, the provider either failed or is missing
    
  return "OK"                                               # All probes passed

def show_single_provider(settings: Box, args: argparse.Namespace) -> None:
  pname = args.provider
  pdata = settings.providers[pname]
  
  if not pdata:
    log.fatal(f'Unknwon provider {pname}, use "netlab show providers" to list valid providers')

  print(f"Status of {pname} ({pdata.description}):")
  print("")
  status = get_provider_status(settings,pname,False)
  print("")
  print(f"Status: {status}")

def show_table(settings: Box, args: argparse.Namespace) -> None:
  heading = ['provider','description','status']

  rows = []
  result = data.get_empty_box()
  for pname in sorted(settings.providers.keys()):
    pdesc = settings.providers[pname].description or ""
    status = get_provider_status(settings,pname,True)
    row = [ pname,pdesc,status ]
    rows.append(row)
    result[pname].description = pdesc
    result[pname].status = status

  if args.format == 'table':
    print('Supported virtualization providers')
    print("")
    strings.print_table(heading,rows,inter_row_line=False)
  elif args.format == 'text':
    for p,d in result.items():
      print(f"{p} ({d.description}): {d.status}")
  else:
    print(strings.get_yaml_string(result))

def show(settings: Box, args: argparse.Namespace) -> None:
  if args.provider:
    show_single_provider(settings,args)
  else:
    show_table(settings,args)
