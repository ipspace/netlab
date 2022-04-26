#
# External provider module
#
import subprocess
import typing
from box import Box

from . import _Provider
from .. import common

def find_link_data(data: Box, node_name: str, ifindex: int) -> Box:
  for intf in data.interfaces:
    if intf.node == node_name and intf.ifindex == ifindex:
        return intf
  return Box({})

class External(_Provider):
  def augment_node_data(self, node: Box, topology: Box) -> None:
    common.print_verbose('Augmenting node data for External')
    # Cleanup MGMT MAC Address (since it's useless for us)
    node.mgmt.pop('mac',None)

  def pre_output_transform(self, topology: Box) -> None:
    # Replace interface names with physical real names, if needed
    for node in topology.nodes.values():
      for intf in node.interfaces:
        link = topology.links[intf.linkindex - 1]
        link_data = find_link_data(link, node.name, intf.ifindex)
        if 'ifname' in link_data:
          common.print_verbose('Found new interface name for node {}'.format(node.name))
          common.print_verbose(' ... Old interface name: {}'.format(intf.ifname))
          common.print_verbose(' ... New interface name: {}'.format(link_data.ifname))
          intf['original_ifname'] = intf['ifname']
          intf['ifname'] = link_data.ifname
          # In case of P2P, rename also left/right
          if link.type == 'p2p':
            for i in ['left','right']:
              if link[i].node == node.name:
                link[i].ifname = link_data.ifname

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

