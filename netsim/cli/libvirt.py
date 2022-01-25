#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import typing
import argparse
import os
import string
import pathlib
import glob
import subprocess

from box import Box

from .. import common
from .. import read_topology
from . import external_commands

def package_parse(args: typing.List[str], settings: Box) -> argparse.Namespace:
  devs = [ k for k in settings.devices.keys() if settings.devices[k].libvirt.create ]
  parser = argparse.ArgumentParser(
    prog='netlab libvirt package',
    description='Package a virtual machine into a libvirt Vagrant box')
  parser.add_argument(
    '-v','--verbose',
    dest='verbose',
    action='count',
    default=0,
    help='Verbose logging')
  parser.add_argument(
    '--skip',
    dest='skip',
    action='store',
    default='',help=argparse.SUPPRESS)
  parser.add_argument(
    dest='device',
    action='store',
    choices=devs,
    help='Network device you want to create')
  parser.add_argument(
    dest='disk',
    action='store',
    type=argparse.FileType('r'),
    help='Virtual machine disk (vmdk or qcow2)')
  return parser.parse_args(args)

def abort_on_failure(cmd: str) -> None:
  if not external_commands.run_command(cmd):
    common.fatal('Aborting')

def lp_create_vm_disk(args: argparse.Namespace) -> None:
  name = args.disk.name

  if 'vmdk' in name:
    print(f"Converting {name} into qcow2 format")
    abort_on_failure(f'qemu-img convert -f vmdk -O qcow2 {name} vm.qcow2')
  else:
    print(f"Creating a copy of {name}")
    abort_on_failure(f'cp {name} vm.qcow2')

def lp_create_vm(args: argparse.Namespace,settings: Box) -> None:
  cmd = settings.devices[args.device].libvirt.create
  cmd = cmd.replace("\n","")
  print(f"""
====================
Starting the VM
====================
We'll start the VM from the newly-created virtual disk. When the
VM starts, execute 'netlab libvirt config {args.device}' in another
window and follow the instructions.
====================

""")
  abort_on_failure(cmd)
  try:
    subprocess.run("virsh destroy vm_box")
  except:
    pass

  try:
    subprocess.run("virsh undefine vm_box")
  except:
    pass

def lp_create_box(args: argparse.Namespace,settings: Box) -> None:
  with open("metadata.json","w") as metadata:
    metadata.write('{"provider":"libvirt","format":"qcow2","virtual_size":4}\n')
    metadata.close()
  print("Downloading vagrant-libvirt create_box.sh script")
  abort_on_failure('curl -O https://raw.githubusercontent.com/vagrant-libvirt/vagrant-libvirt/master/tools/create_box.sh')

  boxfile = f"{args.device}.box"
  if os.path.isfile(boxfile):
    print(f"Removing old {boxfile}")
    os.remove(boxfile)

  abort_on_failure(f'bash create_box.sh vm.qcow2 {boxfile}')

  devdata = settings.devices[args.device]
  boxname = devdata.libvirt.image or devdata.image.libvirt

  if not boxname:
    boxname = input('Enter box name: ')

  version = input('Enter box version: ')
  description = devdata.libvirt.description or devdata.description or (args.device+" box")
  json = string.Template("""
{
  "name": "$boxname",
  "description": "$description",
  "versions": [
    {
      "version": "$version",
      "providers": [
        {
          "name": "libvirt",
          "url": "file://$path/$device.box"
        }
      ]
    }
  ]
}
""")
  print("Creating box metadata in box.json")
  with open("box.json","w") as metadata:
    metadata.write(json.substitute(boxname=boxname,description=description,version=version,device=args.device,path=os.getcwd()))
    metadata.close()
  print("""

Importing Vagrant box
=====================
""")
  if not external_commands.run_command("vagrant box add box.json"):
    print("""

Failed to add Vagrant box. Fix the error(s) and use "vagrant box add box.json" to add it.
""")

def libvirt_package(cli_args: typing.List[str], settings: Box) -> None:
  print("""
=================
     WARNING
=================
This is an experimental script that does its best to build a Vagrant box for libvirt
provider out of a VM disk. It might die a horrible death and leave all sorts of garbage
behind that you'll have to clean up by hand (for example, libvirt 'vm_box' virtual machine).

It also assumes that it can wreak havoc in the current directory (although it will do its
best not to damage the original virtual disk).

""")
  if input('Do you want to continue [Y/n]: ') != 'Y':
    common.fatal('Aborting...')

  args = package_parse(cli_args,settings)
  skip = args.skip

  if not 'disk' in skip:
    lp_create_vm_disk(args)
  if not 'vm' in skip:
    lp_create_vm(args,settings)
  if not 'box' in skip:
    lp_create_box(args,settings)

def config_parse(args: typing.List[str], settings: Box) -> argparse.Namespace:
  moddir = pathlib.Path(__file__).resolve().parent.parent
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

def libvirt_config(cli_args: typing.List[str], settings: Box) -> None:
  args = config_parse(cli_args,settings)
  helpfile = pathlib.Path(__file__).resolve().parent.parent / "install/libvirt" / (args.device+".txt")
  print(helpfile.read_text())

def libvirt_usage() -> None:
  print("Usage: netlab libvirt package|config --help")

def run(cli_args: typing.List[str]) -> None:
  settings = read_topology.read_yaml('package:topology-defaults.yml')
  if not cli_args:
    libvirt_usage()
    return

  if not settings:
    common.fatal("Cannot read the system defaults","libvirt")
    return

  if cli_args[0] == 'package':
    libvirt_package(cli_args[1:],settings)
  elif cli_args[0] == 'config':
    libvirt_config(cli_args[1:],settings)
  else:
    libvirt_usage()
