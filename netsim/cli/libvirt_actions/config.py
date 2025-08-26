#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import argparse
import glob
import pathlib
import typing

from box import Box

from ...utils import files as _files


def config_parse(args: typing.List[str], settings: Box) -> argparse.Namespace:
  moddir = _files.get_moddir()
  devs = map(
    lambda x: pathlib.Path(x).stem,
    glob.glob(str(moddir / "install/libvirt/*txt")))
  parser = argparse.ArgumentParser(
    prog='netlab libvirt config',
    description='Display Vagrant network device box configuration guidelines')
  parser.add_argument(
    dest='device',
    action='store',
    choices=list(devs),
    help='Network device you want to create')
  return parser.parse_args(args)

def run(cli_args: typing.List[str], settings: Box) -> None:
  args = config_parse(cli_args,settings)
  helpfile = _files.get_moddir() / "install/libvirt" / (args.device+".txt")
  print(helpfile.read_text())
