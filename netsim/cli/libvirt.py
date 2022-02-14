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
import shutil

from box import Box

from .. import common
from .. import read_topology
from . import external_commands

def package_parse(args: typing.List[str], settings: Box) -> argparse.Namespace:
  devs = [ k for k in settings.devices.keys() if settings.devices[k].libvirt.create or settings.devices[k].libvirt.create_template ]
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

def get_template_data(devdata: Box) -> Box:
  return devdata + { 'user' : { 'cwd' : os.getcwd() }}

def vm_cleanup(name: str) -> None:
  try:
    subprocess.run(f"virsh destroy {name}".split(" "))
  except Exception as ex:
    print(f"Cannot destroy {name}: {ex}")

  try:
    subprocess.run(f"virsh undefine {name}".split(" "))
  except Exception as ex:
    print(f"Cannot undefine {name}: {ex}")

def lp_create_bootstrap_iso(args: argparse.Namespace,settings: Box) -> None:
  devdata = settings.devices[args.device]
  if not 'create_iso' in devdata.libvirt:
    return
  print("Creating bootstrap ISO image")

  isodir = common.get_moddir() / "install/libvirt" / devdata.libvirt.create_iso
  shutil.rmtree('iso',ignore_errors=True)
  shutil.copytree(isodir,'iso')
  if os.path.exists('bootstrap.iso'):
    os.remove('bootstrap.iso')

  abort_on_failure("mkisofs -l -o bootstrap.iso iso")
  print("... done\n")

def lp_create_vm(args: argparse.Namespace,settings: Box) -> None:
  devdata = settings.devices[args.device]
  print(f"""
====================
Starting the VM
====================
We'll start the VM from the newly-created virtual disk. When the
VM starts, execute 'netlab libvirt config {args.device}' in another
window and follow the instructions.
====================

""")
  if devdata.libvirt.create:
    cmd = devdata.libvirt.create.replace("\n","")
    abort_on_failure(cmd)
  elif devdata.libvirt.create_template:
    data = get_template_data(devdata)
    template = common.template(devdata.libvirt.create_template,data,"install/libvirt",)
    pathlib.Path("template.xml").write_text(template)
    abort_on_failure("virsh define template.xml")
    abort_on_failure("virsh start --console vm_box")

  vm_cleanup('vm_box')

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
  boxname = devdata.libvirt.image
  if not boxname:
    common.fatal("Libvirt box name is not set for device {args.device}")

  print(f"""

=========================
Importing the Vagrant box
=========================
Your Vagrant box is ready to be imported. We just need a few
bits of information to tag it properly so you can have multiple
Vagrant boxes (different software versions) for the same network
device.

""")
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
  args = package_parse(cli_args,settings)
  skip = args.skip

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

  vm_cleanup('vm_box')
  if not 'disk' in skip:
    lp_create_vm_disk(args)
  if not 'iso' in skip:
    lp_create_bootstrap_iso(args,settings)
  if not 'vm' in skip:
    lp_create_vm(args,settings)
  if not 'box' in skip:
    lp_create_box(args,settings)

def config_parse(args: typing.List[str], settings: Box) -> argparse.Namespace:
  moddir = common.get_moddir()
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
  helpfile = common.get_moddir() / "install/libvirt" / (args.device+".txt")
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
