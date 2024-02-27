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
import shutil

from box import Box

from ..utils import strings, status, templates, log, read as _read
from . import external_commands
from . import parser_add_debug, parser_add_verbose
from ..providers.libvirt import create_vagrant_network,LIBVIRT_MANAGEMENT_NETWORK_NAME
from ..utils import files as _files

def package_parse(args: typing.List[str], settings: Box) -> argparse.Namespace:
  devs = [ k for k in settings.devices.keys() if settings.devices[k].libvirt.create or settings.devices[k].libvirt.create_template ]
  parser = argparse.ArgumentParser(
    prog='netlab libvirt package',
    description='Package a virtual machine into a libvirt Vagrant box')
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

  parser_add_verbose(parser)
  parser_add_debug(parser)

  return parser.parse_args(args)

def abort_on_failure(cmd: str) -> None:
  if not external_commands.run_command(cmd):
    log.fatal('Aborting')

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

def vm_cleanup(name: str, ignore_destroy: bool = False, ignore_undefine: bool = False) -> None:
  if not external_commands.run_command(f"virsh destroy {name}",ignore_errors=ignore_destroy):
    if not ignore_destroy:
      log.error(f"Cannot destroy VM {name}",category=log.FatalError,module='libvirt')

  if not external_commands.run_command(f"virsh undefine {name}",ignore_errors=ignore_undefine):
    if not ignore_undefine:
      log.error(f"Cannot undefine VM {name}",category=log.FatalError,module='libvirt')

def start_vagrant_network() -> None:
  create_vagrant_network()
  if not external_commands.run_command(['virsh','net-start',LIBVIRT_MANAGEMENT_NETWORK_NAME]):
    log.fatal(f"Cannot start network {LIBVIRT_MANAGEMENT_NETWORK_NAME}",module='libvirt')

def stop_vagrant_network() -> None:
  if not external_commands.run_command(['virsh','net-destroy',LIBVIRT_MANAGEMENT_NETWORK_NAME]):
    log.error(f"Cannot destroy network {LIBVIRT_MANAGEMENT_NETWORK_NAME}",category=log.FatalError,module='libvirt')

  if not external_commands.run_command(['virsh','net-undefine',LIBVIRT_MANAGEMENT_NETWORK_NAME]):
    log.error(f"Cannot undefine network {LIBVIRT_MANAGEMENT_NETWORK_NAME}",category=log.FatalError,module='libvirt')

def lp_preinstall_hook(args: argparse.Namespace,settings: Box) -> None:
  devdata = settings.devices[args.device]
  if not 'pre_install' in devdata.libvirt:
    return
  print("Running pre-install hooks")
  pre_inst_script = _files.get_moddir() / "install/libvirt" / devdata.libvirt.pre_install / "run.sh"

  if not os.access(pre_inst_script, os.X_OK):
    print(" - run file not executable - skipping.")
    return

  abort_on_failure(pre_inst_script)
  print("... done\n")

def lp_create_bootstrap_iso(args: argparse.Namespace,settings: Box) -> None:
  devdata = settings.devices[args.device]
  if not 'create_iso' in devdata.libvirt:
    return
  print("Creating bootstrap ISO image")

  isodir = _files.get_moddir() / "install/libvirt" / devdata.libvirt.create_iso
  shutil.rmtree('iso',ignore_errors=True)
  shutil.copytree(isodir,'iso')
  if os.path.exists('bootstrap.iso'):
    os.remove('bootstrap.iso')

  abort_on_failure("mkisofs -l --iso-level 4 -o bootstrap.iso iso")
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
    tname = devdata.libvirt.create_template
    try:
      template = templates.render_template(
                  j2_file=tname,
                  data=data,
                  path="install/libvirt")
    except Exception as ex:
      log.fatal(
        text=f"Error rendering {tname}\n{strings.extra_data_printout(str(ex))}",
        module='libvirt')

    pathlib.Path("template.xml").write_text(template)
    abort_on_failure("virsh define template.xml")
    abort_on_failure("virsh start --console vm_box")

  vm_cleanup('vm_box',ignore_destroy=True)        # Have to ignore 'destroy' errors as the VM could be powered off

def lp_create_box(args: argparse.Namespace,settings: Box) -> None:
  _files.create_file_from_text(
    fname="metadata.json",
    txt='{"provider":"libvirt","format":"qcow2","virtual_size":4}\n')
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
    log.fatal("Libvirt box name is not set for device {args.device}")

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

  print(f"""
Your boxes should have versions. A box version can be anything; it's
best to use the version of the network operating system so you'll know
what your boxes do and be able to select a particular OS version in your
lab topology if you feel like building multiple boxes for the same OS.

You might want to limit yourself to using alphanumeric characters and dots.

Examples: 9.3.8 for Nexus OS, 4.27.0M for Arista EOS, 17.03.04 for CSR...

""")
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
  _files.create_file_from_text(
    fname="box.json",
    txt=json.substitute(
      boxname=boxname,
      description=description,
      version=version,
      device=args.device,path=os.getcwd()))
  print("""

Importing Vagrant box
=====================
""")
  if not external_commands.run_command("vagrant box add box.json"):
    print("""

Failed to add Vagrant box. Fix the error(s) and use "vagrant box add box.json" to add it.
""")

def libvirt_package(cli_args: typing.List[str], topology: Box) -> None:
  lab_states = status.read_status(topology)
  if lab_states:
    print('''
netlab cannot create a Vagrant box while there are running labs. Inspect the
status of your lab instances with "netlab status" and stop them with
"netlab down" or "netlab status cleanup --all"
''')
    return
  settings = topology.defaults
  args = package_parse(cli_args,settings)
  log.set_logging_flags(args)
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
  if not strings.confirm('Do you want to continue?'):
    print('User decided to abort the box building process')
    return

  # Set environment variables to ensure we have a consistent LIBVIRT environment
  #
  os.environ["LIBVIRT_DEFAULT_URI"] = "qemu:///system"      # Create system-wide libvirt networks
  os.environ["VIRTINSTALL_OSINFO_DISABLE_REQUIRE"] = "1"    # Stop yammering about unknown operating systems

  # Ignore all errors when doing initial VM cleanup as the VM might not have been created before
  #
  vm_cleanup('vm_box',ignore_destroy=True,ignore_undefine=True)
  start_vagrant_network()
  if not 'preinstall' in skip:
    lp_preinstall_hook(args,settings)
  if not 'disk' in skip:
    lp_create_vm_disk(args)
  if not 'iso' in skip:
    lp_create_bootstrap_iso(args,settings)
  if not 'vm' in skip:
    lp_create_vm(args,settings)
  stop_vagrant_network()
  if not 'box' in skip:
    lp_create_box(args,settings)

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

def libvirt_config(cli_args: typing.List[str], settings: Box) -> None:
  args = config_parse(cli_args,settings)
  helpfile = _files.get_moddir() / "install/libvirt" / (args.device+".txt")
  print(helpfile.read_text())

def libvirt_usage() -> None:
  print("Usage: netlab libvirt package|config --help")

def run(cli_args: typing.List[str]) -> None:
  topology = _read.system_defaults()
  if not topology:
    log.fatal("Cannot read the system defaults","libvirt")

  if not cli_args:
    libvirt_usage()
    return

  if cli_args[0] == 'package':
    try:
      libvirt_package(cli_args[1:],topology)
    except KeyboardInterrupt as ex:
      print("")
      log.error(
        'Aborted by user. VM and management network might still be running',
        category=log.FatalError,
        module='libvirt')
  elif cli_args[0] == 'config':
    libvirt_config(cli_args[1:],topology.settings)
  else:
    libvirt_usage()
