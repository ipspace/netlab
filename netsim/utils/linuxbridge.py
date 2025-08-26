from ..cli import external_commands
from . import log

"""
configure_bridge_forwarding - Enables LLDP (and some other L2 protocols) forwarding on the given Linux bridge

Note that STP or LACP forwarding cannot be enabled this way (in regular Linux kernels).
See https://interestingtraffic.nl/2017/11/21/an-oddly-specific-post-about-group_fwd_mask/ for details
"""
def configure_bridge_forwarding(brname: str) -> bool:
  status = external_commands.run_command(
      ['sudo','sh','-c',f'echo 65528 >/sys/class/net/{brname}/bridge/group_fwd_mask'],
      check_result=True,
      return_stdout=True)
  if status is False:
    return False
  log.print_verbose( f"Enable LLDP forwarding on Linux bridge '{brname}': {status}" )
  return True
