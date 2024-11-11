from . import log
from ..cli import external_commands

"""
configure_bridge_forwarding - Enables LLDP, LACP and 802.1X forwarding on the given Linux bridge
"""
def configure_bridge_forwarding(brname: str) -> bool:
  status = external_commands.run_command(
      ['sudo','sh','-c',f'echo 65528 >/sys/class/net/{brname}/bridge/group_fwd_mask'],
      check_result=True,
      return_stdout=True)
  if status is False:
    return False
  log.print_verbose( f"Enable LLDP,LACP,802.1X forwarding on Linux bridge '{brname}': {status}" )
  return True
