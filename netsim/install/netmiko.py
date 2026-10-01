from box import Box

from netsim.cli import external_commands
from netsim.utils import log, strings


def enable_netmiko(topology: Box, ask: bool) -> None:
  enable_possible = 0
  enable_count = 0

  for d_name,d_data in topology.defaults.devices.items():
    if d_name == 'none':
      continue
    for p_name in [''] + list(topology.defaults.providers.keys()):
      f_name = 'features.initial.config_mode'
      if p_name:                                  # Get global/provider path to the relevant feature
        f_name = p_name + '.' + f_name
      cfg_list = ['netmiko']                      # Netmiko = config via SSH
      if p_name and p_name != 'clab':             # ... but on devices that are not containers...
        cfg_list += ['cp_sh']                     # ... cp_sh means "config via netmiko SCP/SSH"
      p_text = f' with {p_name} provider' if p_name else ''
      enabled = False                             # Remember whether we enabled the feature      
      for cfg_name in cfg_list:                   # Now iterate over all relevant config methods
        if cfg_name not in d_data.get(f_name,[]):
          continue                                # Not available for this device/provider, move on
        g_name = 'group_vars.netlab_config_mode'
        if p_name:                                # Get global/provider path to group variable
          g_name = p_name + '.' + g_name
        g_value = d_data.get(g_name,None)         # Do we already have the device config method set?
        if g_value in cfg_list:                   # Is it one of ours?
          enabled = True
          break                                   # ... cool, we're done, move on
        if g_value:                               # Any other value set for config mode?
          log.info(f'Skipping {d_name}{p_text}: uses {g_value} configuration method')
          break

        enable_possible += 1
        if not ask or strings.confirm(f'Do you want to enable netmiko for {d_name}{p_text}'):
          if not external_commands.run_command(f'netlab defaults --user devices.{d_name}.{g_name}={cfg_name}'):
            log.error(f'Failed to change configuration method for device {d_name}')
          else:
            enabled = True
            enable_count += 1
      if enabled and not p_name:                  # If we have netmiko enabled for the device
        break                                     # ... skip provider-specific checks

  if not enable_possible:
    log.info('Netmiko configuration is already enabled on all supported devices')
  elif enable_count:
    log.info(
      f'Netmiko configuration enabled on {enable_count} devices',
      more_hints=[
        "Use 'netlab defaults --user --regex config_mode' to display devices with user-configured device configuration mode",
        "Use 'netlab defaults --delete --user _parameter_path_' to delete the per-user default setting"])

def post_install(topology: Box) -> bool:
  dont_ask = bool(topology.defaults.netlab.args.yes)
  if dont_ask or strings.confirm('Do you want to enable netmiko configuration on all supported devices',blank_line=True):
    log.info('Enabling netmiko configuration on all supported devices')
    enable_netmiko(topology,ask=False)
  elif not strings.confirm('Do you want to enable netmiko configuration on individual devices'):
    return True
  else:
    enable_netmiko(topology,ask=True)

  return True
