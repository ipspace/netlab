#
# External provider module
#
from box import Box

from ..cli import is_dry_run
from ..utils import log, status
from . import _Provider


class External(_Provider):

  def pre_transform(self,topology : Box) -> None:
    _Provider.pre_transform(self,topology)
    if topology.get('defaults.multilab.id',None):             # Multilab ID is set, use it as the lab ID
      return
    if any(n.get('provider',topology.provider) != 'external' for n in topology.nodes.values()):
      return                                                  # Other providers need the default lab ID

    # Use a unique lab ID (lab name) to allow multiple external labs to be run at once
    topology.defaults.multilab.external = f'external_{topology.name}'

  def augment_node_data(self, node: Box, topology: Box) -> None:
    log.print_verbose('Augmenting node data for External')
    # Cleanup MGMT MAC Address (since it's useless for us)
    node.mgmt.pop('mac',None)

  def pre_start_lab(self, topology: Box) -> None:
    log.print_verbose('pre-start hook for External')
    if log.QUIET:
      return
    
    print('*** Please make sure your physical topology reflects the following cabling:')
    print('')
    with open('external.txt', 'r') as f:
      print(f.read())
    print('')
    print('*** Please make sure your physical topology reflects the above cabling.',flush=True)
    if is_dry_run():                                    # Don't wait for the user in dry-run mode
      return
    if input('Do you want to continue [y/n]: ').lower() != 'y':
      status.unlock_directory()
      status.remove_lab_status(topology)
      log.fatal('Aborting...')
