#
# Vagrant/libvirt provider module
#

import typing

from . import _Provider
from .libvirt import Libvirt
from box import Box

class Virtualbox(_Provider):

  def transform_node_images(self, topology: Box) -> None:
    self.node_image_version(topology)

  @typing.no_type_check
  def get_node_name(self, node: str, topology: Box) -> str:
    return Libvirt.get_node_name(self,node,topology)
