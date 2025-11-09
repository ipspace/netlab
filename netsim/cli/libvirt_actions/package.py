#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import argparse
import os
import pathlib
import re
import shutil
import string
import sys
import tarfile
import typing

from box import Box

from ...providers import get_cpu_model
from ...providers.libvirt import LIBVIRT_MANAGEMENT_NETWORK_NAME, create_vagrant_network
from ...utils import files as _files
from ...utils import log, status, strings, templates
from .. import external_commands, parser_add_debug, parser_add_verbose


def package_parse(args: typing.List[str], settings: Box) -> argparse.Namespace:
  devs = [ k for k in settings.devices.keys() 
               if 'create' in settings.devices[k].libvirt 
                  or settings.devices[k].libvirt.create_template ]
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

"""
Check for running labs and abort if there's a running lab instance
"""
def check_running_labs(topology: Box) -> None:
  lab_states = status.read_status(topology)
  if lab_states:
    print('''
netlab cannot create a Vagrant box while there are running labs. Inspect the
status of your lab instances with "netlab status" and stop them with
"netlab down" or "netlab status cleanup --all"
''')
    sys.exit(1)

  return

"""
Make user confirm they know what they're doing
"""
def box_build_confirm() -> None:
  log.section_header('WARNING','Read this first','yellow')
  print("""
This script tries to build a Vagrant box for libvirt provider out of a VM disk.
It has been tested on Ubuntu and might not work on other Linux distros. It might
also die a horrible death and leave all sorts of garbage behind that you'll have
to clean up by hand (for example, libvirt 'vm_box' virtual machine).

It uses a temporary subdirectory of the /tmp directory, assumes it has enough
disk space there to get the job done, and does its best not to damage the
current directory too much. The Vagrant box will be copied into the current
directory.
""")
  if not strings.confirm('Do you want to continue?'):
    print('User decided to abort the box building process')
    return

"""
Create and destroy the Vagrant management network
"""
def start_vagrant_network() -> None:
  log.section_header('Starting','Create and start the management network')
  create_vagrant_network()
  if not external_commands.run_command(
        ['virsh','net-start',LIBVIRT_MANAGEMENT_NETWORK_NAME],check_result=True):
    log.fatal(f"Cannot start network {LIBVIRT_MANAGEMENT_NETWORK_NAME}",module='libvirt')
  else:
    strings.print_colored_text('[STARTED] ','green',None)
    print('Vagrant management network started')

def stop_vagrant_network(ignore_errors: bool = False) -> None:
  strings.print_colored_text('[CLEANUP] ','green',None)
  print(f'Destroying and undefining network {LIBVIRT_MANAGEMENT_NETWORK_NAME}')
  if not external_commands.run_command(
        ['virsh','net-destroy',LIBVIRT_MANAGEMENT_NETWORK_NAME],
        ignore_errors=ignore_errors,return_stdout=ignore_errors,check_result=True):
    if not ignore_errors:
      log.error(f"Cannot destroy network {LIBVIRT_MANAGEMENT_NETWORK_NAME}",category=log.FatalError,module='libvirt')

  if not external_commands.run_command(
        ['virsh','net-undefine',LIBVIRT_MANAGEMENT_NETWORK_NAME],
        ignore_errors=ignore_errors,return_stdout=ignore_errors,check_result=True):
    if not ignore_errors:
      log.error(f"Cannot undefine network {LIBVIRT_MANAGEMENT_NETWORK_NAME}",category=log.FatalError,module='libvirt')

"""
Cleanup the environment:

* Destroy and undefine the VM
* Delete and undefine the management network
* Cleanup the temporary directory
"""
def vm_cleanup(vm_name: str, ignore_errors: bool = False) -> None:
  strings.print_colored_text('[CLEANUP] ','green',None)
  print('Destroying and undefining vm_box')
  if not external_commands.run_command(
        f"virsh destroy {vm_name}",
        ignore_errors=ignore_errors,return_stdout=ignore_errors,check_result=ignore_errors):
    if not ignore_errors:
      log.error(f"Cannot destroy VM {vm_name}",category=log.FatalError,module='libvirt')

  if not external_commands.run_command(
        f"virsh undefine {vm_name}",
        ignore_errors=ignore_errors,return_stdout=ignore_errors,check_result=ignore_errors):
    if not ignore_errors:
      log.error(f"Cannot undefine VM {vm_name}",category=log.FatalError,module='libvirt')

def cleanup(workdir: typing.Optional[str] = None) -> None:
  log.section_header('Cleanup','Removing vm_box VM and Vagrant management network')
  vm_cleanup('vm_box',ignore_errors=True)
  stop_vagrant_network(ignore_errors=True)
  if workdir and os.path.isdir(workdir):
    strings.print_colored_text('[CLEANUP] ','green',None)
    print(f'Removing the build directory {workdir}')
    shutil.rmtree(workdir)

"""
Create the working directory
"""
def create_workdir(workdir: str, args: argparse.Namespace) -> None:
  if not args.skip:
    if os.path.exists(workdir):
      strings.print_colored_text('[CLEANUP] ','green',None)
      print(f'Removing the old directory {workdir}')
      shutil.rmtree(workdir)

  strings.print_colored_text('[CREATE]  ','green',None)
  print(f'Creating the build directory {workdir}')
  pathlib.Path(workdir).mkdir(parents=True,exist_ok=True,mode=0o777)

"""
Run an external command and abort on failure
"""
def abort_on_failure(cmd: str) -> None:
  if not external_commands.run_command(cmd):
    log.fatal('Aborting')

def lp_create_vm_disk(args: argparse.Namespace, workdir: str) -> None:
  name = args.disk.name

  if name.endswith('.zip'):
    strings.print_colored_text('[UNZIP]   ','green',None)
    print(f"Unzipping {name}")
    abort_on_failure(f'unzip {name}')
    name = name[:-4]

  if '.ova' in name:
    strings.print_colored_text('[UNPACK]  ','green',None)
    print(f"Unpacking OVA archive {name}")
    abort_on_failure(f'tar xvf {name}')
    vmdk = _files.get_globbed_files('.','*.vmdk')
    if not vmdk:
      log.fatal('The OVA archive did not contain a VMDK disk, aborting','libvirt')
    name = vmdk[0]

  if '.vmdk' in name:
    strings.print_colored_text('[CONVERT] ','green',None)
    print(f"Converting {name} into qcow2 format")
    abort_on_failure(f'qemu-img convert -f vmdk -O qcow2 {name} {workdir}/vm.qcow2')
  else:
    strings.print_colored_text('[COPY]    ','green',None)
    print(f"Creating a copy of {name} in {workdir}")
    abort_on_failure(f'cp {name} {workdir}/vm.qcow2')

def get_template_data(devdata: Box) -> Box:
  return devdata + { 'user' : { 'cwd' : os.getcwd() }, 'cpu': get_cpu_model() }

def lp_preinstall_hook(args: argparse.Namespace,settings: Box) -> None:
  devdata = settings.devices[args.device]
  if not 'pre_install' in devdata.libvirt:
    return

  strings.print_colored_text('[EXECUTE] ','green',None)
  print("Running pre-install hooks")
  pre_inst_script = _files.get_moddir() / "install/libvirt" / devdata.libvirt.pre_install / "run.sh"

  if not os.access(pre_inst_script, os.X_OK):
    strings.print_colored_text('[SKIPPED] ','gray',None)

    print("device-specific run.sh file not executable - skipping.")
    return

  abort_on_failure(pre_inst_script)
  strings.print_colored_text('[COMPLETE] ','green',None)
  print("Pre-install hooks completed\n")

def lp_create_bootstrap_iso(args: argparse.Namespace,settings: Box) -> None:
  devdata = settings.devices[args.device]
  if not 'create_iso' in devdata.libvirt:
    return
  strings.print_colored_text('[CREATE]  ','green',None)
  print("Creating bootstrap ISO image")

  isodir = _files.get_moddir() / "install/libvirt" / devdata.libvirt.create_iso
  shutil.rmtree('iso',ignore_errors=True)
  shutil.copytree(isodir,'iso')
  if os.path.exists('bootstrap.iso'):
    os.remove('bootstrap.iso')

  abort_on_failure("mkisofs -l --iso-level 4 -o bootstrap.iso iso")
  strings.print_colored_text('[COMPLETE] ','green',None)
  print("Boostrap ISO image completed\n")

def lp_create_vm(args: argparse.Namespace,settings: Box) -> None:
  devdata = settings.devices[args.device]
  if devdata.libvirt.create is False:
    log.section_header('SKIPPING',"We don't have to start/configure the virtual machine")
    return

  log.section_header('STARTING','Starting the network device virtual machine')
  print(f"""
We'll start the VM from the newly-created virtual disk. When the
VM starts, execute 'netlab libvirt config {args.device}' in another
window and follow the instructions.
===================================================================

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

  vm_cleanup('vm_box',ignore_errors=True)

"""
valid_version: Check the version number
"""
def valid_version(v: str) -> bool:
  match_str = '[0-9a-zA-Z_][.a-zA-Z0-9_-]{0,15}'
  if re.fullmatch(match_str,v):
    return True
  
  log.error(
    f'Box version number can contain ASCII letters, numbers, dots, or dashes',
    category=log.IncorrectValue,
    module='libvirt')
  print()
  return False

def lp_create_box(args: argparse.Namespace,settings: Box,target: str) -> None:
  log.section_header('CREATING','Creating Vagrant box')
  strings.print_colored_text('[INFO]    ','bright_cyan',None)
  print('Retrieving virtual disk size')
  img_json = external_commands.run_command('qemu-img info --output=json vm.qcow2',check_result=True,return_stdout=True)

  try:
    if isinstance(img_json,str) and img_json:
      img_data = Box.from_json(json_string=img_json,box_dots=True)
    else:
      raise Exception('qemu-img failed')
  except Exception as ex:
    log.fatal(f'Cannot parse qemu-img virtual disk information: {ex}')

  v_size = int((img_data['virtual-size'] - 1)/(2**30)) + 1

  strings.print_colored_text('[CREATE]  ','green',None)
  print('Creating Vagrant metadata files')
  _files.create_file_from_text(
    fname="metadata.json",
    txt=f'{{"provider":"libvirt","format":"qcow2","virtual_size":{v_size}}}\n')

  _files.create_file_from_text(
    fname="Vagrantfile",
    txt='''
Vagrant.configure("2") do |config|
  config.vm.provider :libvirt do |libvirt|
    libvirt.driver = "kvm"
    libvirt.host = ""
    libvirt.connect_via_ssh = false
    libvirt.storage_pool_name = "default"
  end
end
''')

  if os.path.isfile(target):
    strings.print_colored_text('[CLEANUP] ','green',None)
    print(f"Removing old {target}")
    os.remove(target)

  strings.print_colored_text('[ARCHIVE] ','green',None)
  print(f'Creating Vagrant box tar archive')
  with tarfile.open(name=target,mode='x') as tar:
    tar.add('Vagrantfile')
    tar.add('metadata.json')
    tar.add('vm.qcow2',arcname='box.img')

def lp_install_box(args: argparse.Namespace,settings: Box) -> None:
  log.section_header('INSTALL','Installing new Vagrant box')
  devdata = settings.devices[args.device]
  boxname = devdata.libvirt.image
  if not boxname:
    log.fatal("Libvirt box name is not set for device {args.device}")

  print(f"""
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
  while True:
    version = input('Enter box version: ')
    if valid_version(version):
      break

  description = devdata.libvirt.description or devdata.description or (args.device+" box")
  json_name = f'{args.device}-{version}-box.json'
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
  strings.print_colored_text('[CREATE]  ','green',None)
  print(f"Creating box metadata in {json_name}")
  _files.create_file_from_text(
    fname=json_name,
    txt=json.substitute(
      boxname=boxname,
      description=description,
      version=version,
      device=args.device,path=os.getcwd()))

  strings.print_colored_text('[IMPORT]  ','green',None)
  print(f"Importing Vagrant box {boxname} version {version}")
  if not external_commands.run_command(f"vagrant box add {json_name}"):
    log.fatal(
      f'Failed to add Vagrant box. Fix the error(s) and use "vagrant box add {json_name}" to add it.','libvirt')

def build(args: argparse.Namespace, topology: Box, workdir: str) -> None:
  skip = args.skip
  box_build_confirm()
  settings = topology.defaults

  # Set environment variables to ensure we have a consistent LIBVIRT environment
  #
  os.environ["LIBVIRT_DEFAULT_URI"] = "qemu:///system"      # Create system-wide libvirt networks
  os.environ["VIRTINSTALL_OSINFO_DISABLE_REQUIRE"] = "1"    # Stop yammering about unknown operating systems

  # Ignore all errors when doing initial VM cleanup as the VM might not have been created before
  #
  cleanup()
  start_vagrant_network()

  homedir = os.path.realpath(os.getcwd())

  if workdir:
    create_workdir(workdir,args)
    os.environ["NETLAB_PACKAGE_WORKDIR"] = workdir          # Pass the build directory to preinstall hooks

  if not 'preinstall' in skip:
    lp_preinstall_hook(args,settings)
  try:
    if not 'disk' in skip:
      lp_create_vm_disk(args,workdir)
    if workdir:
      os.chdir(workdir)
    if not 'iso' in skip:
      lp_create_bootstrap_iso(args,settings)
    if not 'vm' in skip:
      lp_create_vm(args,settings)
    stop_vagrant_network()
    if not 'box' in skip:
      lp_create_box(args,settings,f'{homedir}/{args.device}.box')
    cleanup(workdir=workdir)
  except Exception as ex:
    print()
    os.chdir(homedir)
    strings.print_colored_text('[ABORTED] ','red',None)
    print(f'Aborted due to an exception: {ex}')
    if not skip:
      strings.print_colored_text('[CLEANUP] ','green',None)
      print('Trying to clean up the virsh environment and build directory')
      cleanup(workdir=workdir)

    return

  os.chdir(homedir)
  if not 'install' in skip:
    lp_install_box(args,settings)

def run(cli_args: typing.List[str], topology: Box) -> None:
  check_running_labs(topology)

  settings = topology.defaults
  args = package_parse(cli_args,settings)
  log.set_logging_flags(args)

  workdir = f'/tmp/build_{args.device}'
  try:
    build(args,topology,workdir)
  except KeyboardInterrupt:
    print("")
    log.error(
      'Aborted by user. Trying to clean up',
      category=log.FatalError,
      module='libvirt')
    cleanup(workdir=workdir)
  