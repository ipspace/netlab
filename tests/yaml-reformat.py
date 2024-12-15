#!/usr/bin/env python3
#
import typing
import argparse
import sys
from ruyaml import YAML
from pathlib import Path

def parse() -> typing.Tuple[argparse.Namespace, typing.List[str]]:
  parser = argparse.ArgumentParser(
      prog="yaml-reformat",
      description='Reformat specified YAML files')
  parser.add_argument(
      dest='fname_list', action='store', nargs='+',
      help='Node(s) to run command on')
  return parser.parse_args()

def main() -> None:
  args = parse()
  yaml = YAML()
  for fname in args.fname_list:
    print(f'Reformatting {fname}')
    try:
      doc = yaml.load(Path(fname))
      yaml.dump(doc,Path(fname))
    except Exception as ex:
      print(f'Failed to load {fname}: {ex}')

main()
