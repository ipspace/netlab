#
# External provider module
#
import subprocess
import typing
from box import Box

from . import _Provider
from .. import common

class External(_Provider):
  def augment_node_data(self, node: Box, topology: Box) -> None:
    common.print_verbose('Augmenting node data for External')
    # Cleanup MGMT MAC Address (since it's useless for us)
    node.mgmt.pop('mac',None)

  def pre_start_lab(self, topology: Box) -> None:
    common.print_verbose('pre-start hook for External')
    print('*** Please make sure your physical topology reflects the following cabling:')
    print('')
    with open('external.txt', 'r') as f:
      print(f.read())
    print('')
    print('*** Please make sure your physical topology reflects the above cabling.')
    if input('Do you want to continue [Y/n]: ') != 'Y':
      common.fatal('Aborting...')
