#
# External provider module
#
import subprocess
import typing
from box import Box

from . import _Provider
from ..utils import log,status

class External(_Provider):

  def pre_transform(self,topology : Box) -> None:
    _Provider.pre_transform(self,topology)
    if not topology.get('defaults.multilab.id',None):
      topology.defaults.multilab.id = f'external_{topology.name}'

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
    print('*** Please make sure your physical topology reflects the above cabling.')
    if input('Do you want to continue [y/n]: ').lower() != 'y':
      status.unlock_directory()
      status.remove_lab_status(topology)
      log.fatal('Aborting...')
