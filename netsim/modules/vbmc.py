#
# VirtualBMC module
#
import typing
from box import Box

from . import _Module
from ..utils import log
from .. import data
from ..augment import devices

'''
Check VirtualBMC server node compatibility
'''
def valid_vbmc_server(node: Box, topology: Box) -> bool:
  if not node.get('vbmc.server', False):
    return False

  features = devices.get_device_features(node,topology.defaults)

  if node.get('vbmc.server',False) and not features.vbmc.server:
    log.error(
      f'Node {node.name} cannot be a VirtualBMC server',
      category=log.IncorrectValue,
      module='vbmc')
    return False
  return True

'''
Build the list of VirtualBMC client nodes for the server to manage.
This function creates the vbmc_nodes list that will be used by Ansible tasks.
'''
def build_vbmc_node_list(topology: Box) -> None:
  vbmc_nodes: list[dict[str, typing.Any]] = []
  
  # Find all nodes that are VirtualBMC clients
  for node_name, node in topology.get('nodes', {}).items():
    if not node.get('vbmc.client', False):
      continue
    
    # Build and append IPMI configuration for this client node
    vbmc_node = dict({
      'name': node.get('domain', node_name),
      'ipmi_port': node.get('vbmc.ipmi_port', 6230 + len(vbmc_nodes)),
      'ipmi_address': node.get('vbmc.ipmi_address', '::'),
      'ipmi_user': node.get('vbmc.ipmi_user', 'admin'),
      'ipmi_password': node.get('vbmc.ipmi_password', 'admin'),
    })
    
    vbmc_nodes.append(vbmc_node)
  
  # Store the list in topology for use by server nodes
  topology.vbmc.nodes = vbmc_nodes

'''
Set the vbmc_nodes list in the VirtualBMC server node data
'''
def transform_vbmc_server_config(topology: Box) -> None:

  if not topology.get('vbmc.nodes', False):
    build_vbmc_node_list(topology)

  # Find all VirtualBMC server nodes
  for node_name, node in topology.get('nodes', {}).items():
    if node.get('vbmc.server', False):
      # Copy topology VirtualBMC nodes into server node data
      node.vbmc_nodes = topology.vbmc.nodes

class VBMC(_Module):

  """
  VirtualBMC module transformation:

  * Check server node validity
  * Build list of client nodes for servers to manage
  """
  def module_post_transform(self, topology: Box) -> None:
    for node in topology.nodes.values():
      if not valid_vbmc_server(node, topology):
        continue
      else:
        # Add necessary binds for qemu:///system access
        # VirtualBMC uses this to abstract IPMI actions to libvirt domains
        binds = [
          '/var/run/libvirt/libvirt-sock:/var/run/libvirt/libvirt-sock',
          '/var/run/libvirt/libvirt-sock-ro:/var/run/libvirt/libvirt-sock-ro'
        ]
        for bind in binds:
          data.append_to_list(node.clab, 'binds', bind)

    # Build the client list for all servers
    transform_vbmc_server_config(topology)
