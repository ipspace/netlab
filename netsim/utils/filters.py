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
from jinja2.runtime import StrictUndefined

from ..data import get_a_list, get_box
from ..utils import strings


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
    try:
      addr = netaddr.IPNetwork(value)
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

  if isinstance(value,bool):
    raise ValueError(f'Value passed to ipaddr filter cannot be a bool')

  if arg == '':
    return ipaddr_filter(value,version)

  addr = netaddr.IPNetwork(value)
  try:                                            # It's unclear whether to pass 0 or '0' to Ansible filter to
    arg = int(arg)                                # get the first address in a subnet, so we're accepting both
  except:                                         # and taking a brute-force approach to figuring out if the
    pass                                          # argument is an int cloaked as a string

  if isinstance(arg,int):
    return str(addr[arg]) + "/" + str(addr.prefixlen)
  
  if arg in MAP_IPADDR:
    arg = MAP_IPADDR[arg]

  if arg in ['subnet','host']:
    return str(addr.network) + "/" + str(addr.prefixlen)

  if arg in dir(addr):
    return str(getattr(addr,str(arg)))

  raise ValueError(f'Invalid argument {arg} passed to built-in ipaddr filter')

def j2_ipv4(value: typing.Any, arg: typing.Union[int,str] = '') -> typing.Union[list,str]:
  return j2_ipaddr(value,arg,4)

def j2_ipv6(value: typing.Any, arg: typing.Union[int,str] = '') -> typing.Union[list,str]:
  return j2_ipaddr(value,arg,6)

# Format MAC addresses in Cisco/Unix/... format
#
def j2_hwaddr(value: typing.Any, format: str = '') -> str:
  try:
    mac = netaddr.EUI(value)                      # Try to parse the value as MAC address
    if format == 'linux':                         # linux format is a synonym for unix
      format = 'unix_expanded'
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

# Fail template rendering with a custom error message
#
def j2_fail(msg: str) -> None:
  """
  Jinja2 global function to fail template rendering with a custom error message.
  Use in templates: {{ fail('Error message') }}
  """
  raise ValueError(msg)

class j2_Undefined(StrictUndefined):
  """
  Mimics Ansible's undefined variable handling in Jinja2 templates.
  Accessing attributes or items of an undefined variable returns another undefined,
  and expressions like 'x.y is defined' return False when x is undefined,
  rather than raising an error.
  """

  # Override attribute access
  def __getattr__(self, name: typing.Any) -> typing.Any:
      return j2_Undefined(name=name, hint=self._undefined_hint)

  # Override item access
  def __getitem__(self, key: typing.Any) -> typing.Any:
      return j2_Undefined(name=key, hint=self._undefined_hint)

  # Override boolean evaluation
  def __bool__(self) -> bool:
      return False

  # Override is defined
  @property
  def defined(self) -> bool:
      return False

UTILS_FILTERS: dict = {
  'ipaddr': j2_ipaddr,
  'ipv4': j2_ipv4,
  'ipv6': j2_ipv6,
  'hwaddr': j2_hwaddr
}

"""
Simplified 'flatten' filter -- returns a flattened list
"""
def bi_flatten(f_list: typing.Any, levels: typing.Optional[int] = None) -> list:
  mylist = get_a_list(f_list)
  result = []
  for value in mylist:
    if isinstance(value,list):
      if (levels is None or levels >= 1):
        result.extend(bi_flatten(value,None if levels is None else levels - 1))
      else:
        result.extend(value)
    else:
      result.append(value)

  return result      

"""
Simplified 'difference' filter -- returns a difference between two lists
"""
def bi_difference(src: typing.Any, diff: typing.Any) -> list:
  diff_list = get_a_list(diff)
  src_list = get_a_list(src)
  return [ x for x in src_list if x not in diff_list ]

"""
Render value into YAML. The additional arguments accepted by the Ansible version of the filter are ignored
"""
def bi_yaml(src: typing.Any, **kwargs: typing.Any) -> str:
  if isinstance(src,dict):                            # Ensure the input dictionary is sorted by keys
    src = { k:src[k] for k in sorted(src.keys()) }    # ... to keep 1:1 compatibility with Ansible configs
                                                      # ... that get their data from sorted inventory files
  yaml = strings.get_yaml_string(src)
  if '---\n' in yaml:
    yaml = yaml.split('---\n')[1]

  return yaml

"""
Merge two dictionaries
"""
def bi_merge(d1: typing.Any, d2: typing.Any) -> dict:
  if not isinstance(d1,dict) or not isinstance(d2,dict):
    raise ValueError('Parameters to combine/merge filter must be dictionaries')

  result = get_box(d1) + get_box(d2)
  return result.to_dict()

BUILTIN_FILTERS: dict = {
  'combine': bi_merge,
  'difference': bi_difference,
  'flatten': bi_flatten,
  'to_yaml': bi_yaml,
  'to_nice_yaml': bi_yaml
}
