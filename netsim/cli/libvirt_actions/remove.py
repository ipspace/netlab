#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import argparse
import typing

from box import Box

from ...utils import log, strings
from .. import error_and_exit, external_commands


def remove_parse(args: typing.List[str], settings: Box) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog='netlab libvirt remove',
    description='Remove a libvirt Vagrant box')
  parser.add_argument(
    dest='device',
    action='store',
    nargs='?',
    help='Remove a Vagrant box for the specified device')
  parser.add_argument(
    '--box',
    dest='box',
    action='store',
    help='Specify the Vagrant box you want to remove')
  parser.add_argument(
    '--version',
    dest='version',
    action='store',
    help='Specify the version of the Vagrant box you want to remove')
  parser.add_argument(
    '--cleanup',
    dest='cleanup',
    action='store_true',
    help='Remove the volume(s) related to the specified Vagrant box')
  parser.add_argument(
    '--pool',
    dest='pool',
    action='store',
    default='default',
    help="Specify the libvirt storage pool ('default' usually works)")

  return parser.parse_args(args)

"""
Generic abort message -- set the correct module and don't try to print topo header
"""
def abort(msg: str) -> None:
  print()
  log.fatal(msg,module='libvirt',header=False)

"""
Run an external command and abort on failure
"""
def abort_on_failure(cmd: str) -> None:
  if not external_commands.run_command(cmd,ignore_errors=True):
    abort(f'The {cmd} command failed, aborting')

"""
Print all versions of the specified box we found
"""
def print_box_versions(args: argparse.Namespace,box_list: list) -> None:
  print(f'Vagrant has these box versions for the {args.box} box:\n')
  print("\n".join(box_list))

"""
Find the Vagrant box the user wants to remove
"""
def find_vagrant_box(args: argparse.Namespace) -> None:
  log.section_header('Starting','Trying to find the Vagrant box to remove')
  boxes = external_commands.run_command(
            ['vagrant','box','list'],
            check_result=True, ignore_errors=True, return_stdout=True, run_always=True)
  if not isinstance(boxes,str) or not boxes:
    abort('Cannot get the list of Vagrant boxes')

  # note: str(boxes) used just to keep mypy happy
  box_list = [ line for line in str(boxes).split('\n') if line.startswith(args.box+' ') ]
  if not box_list:
    abort(f'The Vagrant box {args.box} cannot be found')

  box_libvirt = [ line for line in box_list if '(libvirt' in line ]
  if not box_libvirt:
    print_box_versions(args,box_list)
    abort('The specified Vagrant box exists, but is not for the libvirt provider')

  if args.version:
    box_versions = [ line for line in box_libvirt if ', '+args.version in line ]
    if not box_versions:
      print_box_versions(args,box_list)
      abort('The specified box version does not exist')

    return

  if len(box_libvirt) > 1:
    print_box_versions(args,box_libvirt)
    abort('You have to specify the box version you want to remove with the --version argument')

  box_info = box_libvirt[0].split('(')[1]
  box_version = box_info.split(', ')[1].replace(')','')
  if not box_version:
    print_box_versions(args,box_libvirt)
    abort('This script is too stupid to find the box version, please use the --version argument')

  args.version = box_version
  return

"""
Make user confirm they know what they're doing
"""
def box_remove_confirm(args: argparse.Namespace) -> None:
  log.section_header('WARNING','Read this first','yellow')

  print('\nThis command will remove Vagrant box ',end='')
  strings.print_colored_text(args.box,'bold',None)
  print(' version ',end='')
  strings.print_colored_text(args.version,'bold',None)
  print(f"""

It will also try to remove the corresponding libvirt volume. Use the --cleanup
argument to remove all libvirt volumes for the specified box if the removal of
the libvirt volume fails.

Needless to say, you'll have to reinstall or rebuild the Vagrant box if you make
a wrong choice.
""")
  if not strings.confirm('Do you want to continue?'):
    abort('User decided to abort the Vagrant box removal')

def volume_purge_confirm(args: argparse.Namespace) -> None:
  log.section_header('WARNING','Read this first','yellow')

  print('\nThis command will remove libvirt volumes related to Vagrant box ',end='')
  strings.print_colored_text(args.box,'bold',None)
  print('\nfrom storage pool ',end='')
  strings.print_colored_text(args.pool,'bold',None)
  print(f"""

We're pretty sure the command identifies only the volumes related to Vagrant
boxes unless you're creating libvirt volumes yourself and use some weird naming
scheme. Deleting these volumes is usually not risky as Vagrant recreates them
from the Vagrant boxes the next time you start the virtual machines using them.
        
The volumes should be in the 'default' pool. If that fails, use 'virsh
pool-list' to list the storage pools and specify the pool you're using with the
--pool argument.
""")
  if not strings.confirm('Do you want to continue?'):
    abort('User decided not to purge libvirt volumes')

def purge_volume(args: argparse.Namespace) -> None:
  if args.version == '0':
    args.version = None
  vol_box = args.box + (":"+args.version if args.version else "")
  prefix = args.box.replace('/','-VAGRANTSLASH-')
  suffix = (args.version or '') + '_box.img'

  log.section_header('Cleanup',f'Finding libvirt volumes matching the {vol_box} box')
  volumes = external_commands.run_command(
            ['virsh','vol-list','--pool',args.pool],
            check_result=True, ignore_errors=True, return_stdout=True, run_always=True)

  if not isinstance(volumes,str) or not volumes:
    abort(f'Failed to fetch the list of volumes in storage pool {args.pool}')

  vol_names = [ line.split()[0] for line in str(volumes).split('\n') if line ]
  vol_match = [ line for line in vol_names if line.startswith(prefix) and line.endswith(suffix) ]
  if not vol_match:
    print(f'Cannot find any volumes that would be created from the {vol_box} Vagrant box')
    return

  print(f'Volumes matching the {vol_box} Vagrant box:',end="\n\n")
  print("\n".join(vol_match),end="\n\n")
  if not strings.confirm('Do you want to remove these volumes'):
    abort('Not removing the libvirt volumes')

  OK = True
  for vol in vol_match:
    OK = OK and bool(external_commands.run_command(
                        [ 'virsh','vol-delete',vol,'--pool',args.pool ],
                        ignore_errors=True))
  
  if OK:
    strings.print_colored_text('[SUCCESS] ','green',None)
    print(f"Removed libvirt volumes")
  else:
    strings.print_colored_text('[FAILED]  ','red',None)
    print(f"Some volumes could not be removed")

def remove_box(args: argparse.Namespace) -> None:
  box_remove_confirm(args)
  strings.print_colored_text('[CLEANUP] ','green',None)
  print(f'Removing vagrant box {args.box}:{args.version}')
  abort_on_failure(f'vagrant box remove {args.box} --provider libvirt --box-version {args.version}')
  strings.print_colored_text('[SUCCESS] ','green',None)
  print(f"Removed vagrant box {args.box}:{args.version}")
  purge_volume(args)

def run(cli_args: typing.List[str], topology: Box) -> None:
  settings = topology.defaults
  args = remove_parse(cli_args,settings)
  use_show = 'Use "netlab show images -p libvirt" to display devices with libvirt Vagrant boxes'

  if args.device and args.box:
    abort('You can specify a device or a box name but not both')
  if args.device:
    if args.device not in settings.devices:
      error_and_exit(f'Invalid device {args.device}',more_hints=use_show)
    args.box = topology.defaults.devices[args.device].libvirt.image
    if not args.box:
      error_and_exit(
        f'netlab defaults do not specify the libvirt Vagrant box name for {args.device}',
        more_hints=use_show)
  if args.cleanup:
    volume_purge_confirm(args)
    purge_volume(args)
  else:
    if not args.box:
      error_and_exit('You have to specify a device or a Vagrant box',more_hints=use_show)
    find_vagrant_box(args)
    remove_box(args)
