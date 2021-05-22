#
# Vagrant/libvirt provider module
#
from box import Box

from . import Provider

class Containerlab(Provider):

  def augment_node_data(self, node: Box, topology: Box) -> None:
    node.hostname = "clab-%s-%s" % (topology.name,node.name)
