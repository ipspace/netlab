#
# Vagrant/libvirt provider module
#
import typing
from box import Box

from . import _TopologyOutput,check_writeable
from .. import providers
from ..augment import nodes
from ..utils import log,strings

def get_provider_module(topology: Box, provider: str) -> providers._Provider:
  return providers._Provider.load(provider,topology.defaults.providers[provider])

def write_provider_file(topology: Box, provider: str, filename: typing.Optional[str]) -> None:
  p_module = get_provider_module(topology,provider)
  p_module.create(topology,filename)

class ProviderConfiguration(_TopologyOutput):

  DESCRIPTION :str = 'Create virtualization provider configuration file(s)'

  def write(self, topology: Box) -> None:
    check_writeable('provider configuration')
    filename = None
    if hasattr(self,'filenames'):
      filename = self.filenames[0]
      if len(self.filenames) > 1:
        log.error('Extra output filename(s) ignored: %s' % str(self.filenames[1:]),log.IncorrectValue,'provider')

    if self.format:
      log.error('Specified output format(s) %s ignored' % self.format,log.IncorrectValue,'provider')

    # Creates a "ghost clean" topology after transformation
    # (AKA, remove unmanaged devices)
    topology = nodes.ghost_buster(topology)
    p_module = get_provider_module(topology,topology.provider)
    providers.mark_providers(topology)
    p_module.call('pre_output_transform',topology)
    write_provider_file(providers.select_topology(topology,topology.provider),topology.provider,filename)

    for subprovider in topology[topology.provider].providers.keys():  # Iterate over subproviders
      strings.print_colored_text('[INFO]    ','bright_cyan',alt_txt=None)
      print(f"Creating configuration file for secondary provider {subprovider}")
      write_provider_file(
        topology=providers.select_topology(topology,subprovider),
        provider=subprovider,
        filename=topology.defaults.providers[topology.provider][subprovider].filename)