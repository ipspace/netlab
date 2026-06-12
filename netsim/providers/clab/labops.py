#
# Containerlab provider module
#
import pathlib

from box import Box

from ...augment import devices
from ...cli import external_commands, is_dry_run
from ...data import append_to_list, get_empty_box
from ...data.types import must_be_dict
from ...utils import linuxbridge, log, strings


def use_ovs_bridge( topology: Box ) -> bool:
  return topology.defaults.providers.clab.bridge_type == "ovs-bridge"

def create_linux_bridge( brname: str ) -> bool:
  if external_commands.run_command(
       ['brctl','show',brname],check_result=True,ignore_errors=True) and not is_dry_run():
    log.print_verbose(f'Linux bridge {brname} already exists, skipping')
    return True

  status = external_commands.run_command(
      ['sudo','ip','link','add','name',brname,'type','bridge'],check_result=True,return_stdout=True)
  if status is False:
    return False
  log.print_verbose( f"Created Linux bridge '{brname}': {status}" )

  status = external_commands.run_command(
      ['sudo','ip','link','set','dev',brname,'up'],check_result=True,return_stdout=True)
  if status is False:
    return False
  log.print_verbose( f"Enable Linux bridge '{brname}': {status}" )

  status = linuxbridge.configure_bridge_forwarding(brname)
  return status

def destroy_linux_bridge( brname: str ) -> bool:
  status = external_commands.run_command(
      ['sudo','ip','link','del','dev',brname],check_result=True,return_stdout=True)
  if status is False:
    return False
  log.print_verbose( f"Delete Linux bridge '{brname}': {status}" )
  return True

_OVS_OK: bool = False
def check_ovs_installation() -> None:
  global _OVS_OK
  if _OVS_OK:
    return

  if not external_commands.has_command('ovs-vsctl'):
    log.error(
      'Open vSwitch package is not installed, you cannot use OVS bridges with containerlab',
      more_hints = [
        'This error was caused by defaults.providers.clab.bridge_type being set to ovs-bridge',
        'Use "sudo apt install openvswitch-switch" on Ubuntu or an equivalent command to install Open vSwitch'],
      category=log.FatalError,
      module='clab')
    log.exit_on_error()

  _OVS_OK = True

def create_ovs_bridge( brname: str ) -> bool:
  check_ovs_installation()
  status = external_commands.run_command(
      ['sudo','ovs-vsctl','add-br',brname],check_result=True,return_stdout=True)
  if status is False:
    return False
  log.print_verbose( f"Create OVS bridge '{brname}': {status}" )
  return True

def destroy_ovs_bridge( brname: str ) -> bool:
  status = external_commands.run_command(
      ['sudo','ovs-vsctl','del-br',brname],check_result=True,return_stdout=True)
  if status is False:
    return False
  log.print_verbose( f"Delete OVS bridge '{brname}': {status}" )
  return True

'''
get_loaded_kernel_modules: Get the list of loaded kernel modules from '/proc/modules'
'''
def get_loaded_kernel_modules() -> list:
  mod_list = pathlib.Path('/proc/modules').read_text().split('\n')
  return [ line.split(' ')[0] for line in mod_list ]

'''
load_kmods: Load kernel modules before starting containers

The kernel modules needed for individual netlab modules are defined in provider- or device 'kmods'
dictionary. If the device 'kmods' value is 'None' then the device uses the standard setup, otherwise
you could specify which kernel modules you want to load.
'''
def load_kmods(topology: Box) -> None:
  defs = topology.defaults
  clab_kmods = defs.providers.clab.kmods
  kmod_list  = get_empty_box()

  for ndata in topology.nodes.values():                     # Iterate over all nodes
    if ndata.get('provider') != 'clab':                     # The node is not using clab provider, move on
      continue
    ddata = devices.get_provider_data(ndata,defs)           # Get device data for the current node
    if 'kmods' not in ddata:                                # Kmods attribute is not there, the device is not using kernel modules
      continue
    must_be_dict(ddata,'kmods',path=f'defaults.devices.{ndata.device}.clab',create_empty=True)
    kdata = clab_kmods + ddata.kmods                        # Merge device-specific modules with system-wide kernel module definition

    # At this point, we have device-specific dictionary mapping netlab modules into kernel modules
    #
    for m in (['initial']+ndata.get('module',[])):          # Now iterate over all the netlab modules the node uses
      if m not in kdata:                                    # ... and if the netlab modules does not need kernel modules
        continue                                            # ... move on
      for kmod in kdata[m]:                                 # Next, add individual kernel modules in the kdata entry
        append_to_list(kmod_list,m,kmod)                    # ... to the module-specific list of kernel mdules

  # Now we have lists of kernel modules that have to be loaded based on netlab modules used in lab topology
  # Next step: for every netlab module, load the missing kernel modules
  #
  for m in kmod_list.keys():
    loaded_kmods = get_loaded_kernel_modules()
    needed_kmods = [ kmod for kmod in kmod_list[m] if kmod.replace('?','') not in loaded_kmods ]
    if not needed_kmods:
      continue

    # Any required modules? If so, print the message
    #
    if [ kmod for kmod in needed_kmods if '?' not in kmod ] or log.VERBOSE:
      mod_names = [ kmod.replace('?','') for kmod in needed_kmods ]
      strings.print_colored_text('[LOADING] ','bright_cyan',None)
      print(f'Loading Linux kernel modules {",".join(mod_names)} required by containers using {m} module',flush=True)

    for kmod in needed_kmods:
      load_mod = kmod.replace('?','')                       # Get the true module name
      status = external_commands.run_command(
        ['sudo','modprobe',load_mod ],
        ignore_errors=True,
        check_result=not log.VERBOSE,                       # Hide STDOUT if we're not in verbose mode
        return_stdout=not log.VERBOSE)                      # ... so we won't annoy users for optional module failures
      if status is False:
        if '?' not in kmod:
          log.error(f'Cannot load Linux kernel module {load_mod}',log.IncorrectValue,'clab')
        elif log.VERBOSE:
          log.info(f'Cannot load optional Linux kernel module {load_mod}')

  log.exit_on_error()
