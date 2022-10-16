#
# Vagrant/libvirt provider module
#
from box import Box

from . import _TopologyOutput
from .. import providers
from .. import common
from ..augment import nodes

class ProviderConfiguration(_TopologyOutput):

  def write(self, topology: Box) -> None:
    provider = providers._Provider.load(topology.provider,topology.defaults.providers[topology.provider])
    provider.call('pre_output_transform',topology)

    # Creates a "ghost clean" topology after transformation
    # (AKA, remove unmanaged devices)
    provider_topology = nodes.ghost_buster(topology)

    filename = None
    if hasattr(self,'filenames'):
      filename = self.filenames[0]
      if len(self.filenames) > 1:
        common.error('Extra output filename(s) ignored: %s' % str(self.filenames[1:]),common.IncorrectValue,'provider')

    if self.format:
      common.error('Specified output format(s) %s ignored' % self.format,common.IncorrectValue,'provider')

    provider.create(provider_topology,filename)
