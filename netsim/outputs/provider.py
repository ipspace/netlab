#
# Vagrant/libvirt provider module
#
import typing
from box import Box

from . import _TopologyOutput
from .. import providers
from .. import common
from ..augment import nodes

def get_provider_module(topology: Box, provider: str) -> providers._Provider:
  return providers._Provider.load(provider,topology.defaults.providers[provider])

def write_provider_file(topology: Box, provider: str, filename: typing.Optional[str]) -> None:
  p_module = get_provider_module(topology,provider)
  p_module.create(topology,filename)

class ProviderConfiguration(_TopologyOutput):

  def write(self, topology: Box) -> None:
    filename = None
    if hasattr(self,'filenames'):
      filename = self.filenames[0]
      if len(self.filenames) > 1:
        common.error('Extra output filename(s) ignored: %s' % str(self.filenames[1:]),common.IncorrectValue,'provider')

    if self.format:
      common.error('Specified output format(s) %s ignored' % self.format,common.IncorrectValue,'provider')

    # Creates a "ghost clean" topology after transformation
    # (AKA, remove unmanaged devices)
    topology = nodes.ghost_buster(topology)
    p_module = get_provider_module(topology,topology.provider)
    providers.mark_providers(topology)
    p_module.call('pre_output_transform',topology)
    write_provider_file(providers.select_topology(topology,topology.provider),topology.provider,filename)

    for subprovider in topology[topology.provider].providers.keys():  # Iterate over subproviders
      print(f"Creating configuration file for secondary provider {subprovider}")
      write_provider_file(
        topology=providers.select_topology(topology,subprovider),
        provider=subprovider,
        filename=topology.defaults.providers[topology.provider][subprovider].filename)