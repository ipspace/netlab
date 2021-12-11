#
# Vagrant/libvirt provider module
#

from . import _Provider
from box import Box

class Virtualbox(_Provider):

  def transform_node_images(self, topology: Box) -> None:
    self.node_image_version(topology)
