#
# VPP quirks
#
from box import Box

from ..augment import devices
from ..data import append_to_list
from . import _Quirks


class Vpp(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    if devices.get_provider(node, topology) != "clab":
      return

    append_to_list(node, "config", "config-done")
    node._daemon_config.setup = "/etc/vpp/setup.conf"
    append_to_list(node, "netlab_ansible_skip_module", "setup")
