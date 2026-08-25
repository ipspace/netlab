#
# Vagrant/libvirt provider module
#


from box import Box

from ...cli import external_commands
from ...data import get_empty_box
from ...utils import log, strings

"""
Copy the memory usage from the 'virsh domstats' data of a single VM into the lab status data.

The libvirt domain name is '<lab_prefix>_<node>' while the lab status data is keyed by the
Vagrant machine name (<node>), so we have to find the matching lab status entry. Domains
belonging to some other lab (or to a VM not managed by netlab) are silently ignored.

Without a balloon driver in the guest OS we cannot get the memory the VM uses on the host
and have to report the assigned memory instead (flagged with 'max' to avoid confusion).
"""
def set_vm_memory(stat_box: Box, vm_name: str, vm_stats: Box) -> None:
  for wk_name in stat_box:
    if vm_name != wk_name and not vm_name.endswith(f'_{wk_name}'):
      continue

    try:
      if 'balloon.rss' in vm_stats:
        stat_box[wk_name].memory = strings.format_memory_size(int(vm_stats['balloon.rss']))
      elif 'balloon.current' in vm_stats:
        stat_box[wk_name].memory = strings.format_memory_size(int(vm_stats['balloon.current'])) + ' (max)'
    except ValueError as ex:
      log.print_verbose(f'Cannot get the memory usage of libvirt domain {vm_name}: {ex}')

    return

def add_memory_usage(stat_box: Box) -> None:
  """
  Add the memory usage of the lab VMs to the lab status data.

  'virsh domstats --balloon' reports (in KB) the resident set size of the QEMU process
  (balloon.rss -- the memory the VM actually uses on the host) and the memory assigned to
  the VM (balloon.current). The RSS value is available only when the VM runs a balloon
  driver or a guest agent; without it, we can report only the assigned memory.

  Vagrant knows the VMs as 'r1' while libvirt calls them '<lab_prefix>_r1', so we have to
  match the libvirt domain names with the Vagrant machine names we already know about.

  Failures are non-fatal -- memory usage is extra information, not a prerequisite for
  displaying the lab status.
  """
  try:
    virsh_stats = external_commands.run_command(
                'virsh domstats --balloon --list-running',
                check_result=True,
                ignore_errors=True,
                return_stdout=True,
                run_always=True)
  except Exception as ex:
    log.print_verbose(f'Cannot execute "virsh domstats": {ex}')
    return

  if not isinstance(virsh_stats,str):
    return

  vm_name = None
  vm_stats = get_empty_box()
  for line in virsh_stats.split('\n') + [ 'Domain: end-of-data' ]:
    line = line.strip()
    if line.startswith('Domain:'):                        # Start of a new domain, save the previous one
      if vm_name is not None:
        set_vm_memory(stat_box,vm_name,vm_stats)
      vm_name = line.split("'")[1] if "'" in line else None
      vm_stats = get_empty_box()
    elif '=' in line:
      (k,v) = line.split('=',1)
      vm_stats[k] = v

def get_lab_status(collect_status: dict) -> Box:
  try:
    status = external_commands.run_command(
                'vagrant status --machine-readable',
                check_result=True,
                ignore_errors=True,
                return_stdout=True)
    
    stat_box = get_empty_box()
    if not isinstance(status,str):
      return stat_box
    try:
      for line in status.split('\n'):
        items = line.split(',')
        if len(items) >= 4:
          if items[2] == 'state-human-short':
            stat_box[items[1]].status = items[3]
    except Exception as ex:
      log.error(f'Cannot get Vagrant status: {ex}',category=log.FatalError,module='libvirt')
      return stat_box

    if collect_status.get('memory',False):
      add_memory_usage(stat_box)
    return stat_box
  except Exception as ex:
    log.error(f'Cannot execute "vagrant status --machine-readable": {ex}',category=log.FatalError,module='libvirt')
    return get_empty_box()
