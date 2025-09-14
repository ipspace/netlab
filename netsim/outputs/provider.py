#
# Vagrant/libvirt provider module
#
import typing

from box import Box

from .. import providers
from ..augment import nodes
from ..utils import log, strings
from . import _TopologyOutput, check_writeable
from . import common as output_common


def write_provider_file(topology: Box, provider: str, filename: typing.Optional[str]) -> None:
  p_module = providers.get_provider_module(topology,provider)
  p_module.create(topology,filename)

class ProviderConfiguration(_TopologyOutput):

  DESCRIPTION :str = 'Create virtualization provider configuration file(s)'

  def write(self, topology: Box) -> None:
    check_writeable('provider configuration')
    filename = self.select_output_file(missing_OK=True)
    if self.format:
      log.error(f'Specified output format(s) {self.format} ignored',log.IncorrectValue,'provider')

    # Creates a "ghost clean" topology after transformation
    # (AKA, remove unmanaged devices)
    topology = output_common.create_adjusted_topology(nodes.ghost_buster(topology),ignore=[])
    p_module = providers.get_provider_module(topology,topology.provider)
    providers.mark_providers(topology)
    p_module.call('pre_output_transform',topology)
    log.exit_on_error()
    write_provider_file(providers.select_topology(topology,topology.provider),topology.provider,filename)

    for subprovider in topology[topology.provider].providers.keys():  # Iterate over subproviders
      strings.print_colored_text('[INFO]    ','bright_cyan',alt_txt=None)
      print(f"Creating configuration file for secondary provider {subprovider}")
      write_provider_file(
        topology=providers.select_topology(topology,subprovider),
        provider=subprovider,
        filename=topology.defaults.providers[topology.provider][subprovider].filename)