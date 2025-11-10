# Networking-specific Jinja2 filters
#
# These filters replace the functionality of Ansible filters for templates rendered inside
# netlab (provider configurations, reports, container files, daemon configs...) because
# the crazy "we don't like _" decision introduced in Ansible release 12 breaks too many of them
#
# We're using slightly different filter names on purpose to identify any potential use of
# Ansible filters
#
# Please note that the filter names have to start with 'j2_' -- that's how the template module
# identifies them as Jinja2 filters
#

import typing

import netaddr


def ipaddr_filter(
      value: typing.Any,
      version: typing.Optional[int] = None) -> typing.Union[list,str]:

  # If the IP address filter gets a list of values it recursively evaluates itself
  # on each value in the list, the returns a list of non-empty values
  #
  if isinstance(value,list):
    f_list: list = [ ipaddr_filter(f_value,version) for f_value in f_list ]
    return [ f_value for f_value in f_list if f_value ]

  try:
    addr = netaddr.IPAddress(value)
    return str(addr) if version is None or version == addr.version else ''
  except:
    return ''

MAP_IPADDR: dict = {
  'address': 'ip',
  'prefix':  'prefixlen'
}

def j2_ipaddr(
      value: typing.Any,
      arg: typing.Union[int,str] = '',
      version: typing.Optional[int] = None) -> typing.Union[list,str]:
  global MAP_IPADDR

  if arg == '':
    return ipaddr_filter(value,version)

  addr = netaddr.IPNetwork(value)
  if isinstance(arg,int):
    return str(addr[arg])
  
  if arg in MAP_IPADDR:
    arg = MAP_IPADDR[arg]

  if arg in ['subnet']:
    return str(addr.network) + "/" + str(addr.prefixlen)

  if arg in dir(addr):
    return str(getattr(addr,str(arg)))

  raise ValueError(f'Invalid argument {arg} passed to built-in ipaddr filter')

def j2_ipv4(value: typing.Any, arg: typing.Union[int,str]) -> typing.Union[list,str]:
  return j2_ipaddr(value,arg,4)

def j2_ipv6(value: typing.Any, arg: typing.Union[int,str]) -> typing.Union[list,str]:
  return j2_ipaddr(value,arg,6)

# Format MAC addresses in Cisco/Unix/... format
#
def j2_hwaddr(value: typing.Any, format: str = '') -> str:
  try:
    mac = netaddr.EUI(value)                      # Try to parse the value as MAC address
    if format == 'linux':                         # linux format is a synonym for unix
      format = 'unix'
    fmt = getattr(netaddr,f'mac_{format}')        # Try to get formatting constant
    if not fmt:                                   # ... unknown constant?
      raise ValueError(f'Invalid format {format} used in built-in hwaddr filter')
    else:
      return mac.format(dialect=fmt)              # All good, try to return the formatted MAC address
  except:                                         # Value is not a MAC address :(
    if format:                                    # If the user tried to format it, throw an error
      raise ValueError(f'{value} is not a valid MAC address and cannot be formatted as {format}')
    else:                                         # Otherwise it was a filter query, return empty string
      return ''
