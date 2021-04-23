#
# Vagrant/libvirt provider module
#

from . import Provider

class Containerlab(Provider):

  def augment_node_data(self,node,topology):
    node.hostname = "clab-%s-%s" % (topology.name,node.name)
