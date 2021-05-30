'''
Set up network addressing
=========================

The network topology needs three types of addressing pools:

* Loopback addresses
* P2P addresses
* LAN and stub link addresses

Each pool could have IPv4 and IPv6 component. Alternatively, a pool
could be unnumbered (using IPv6 LLA and IPv4 address from loopback interface).

Notes:
* _lan_ pool is used for stub and P2P prefixes if the corresponding
  pools are not defined

The addressing pools are set up in _addressing_ part of topology
defaults (local or global), for example:

addressing:
  lan:
    ipv4: 172.16.0.0/16
    ipv6: 2008:db8:0100::/48
    prefix: 24
  p2p:
    ipv4: 10.1.0.0/16
    prefix: 30
  loopback:
    ipv4: 10.0.0.0/24

IPv4 component of an addressing pool is defined with two parameters:

* _ipv4_ prefix - IPv4 addressing space used by the pool
* _prefix_ length - prefix length of individual subnets in the pool

IPv6 component of an addressing pool is defined with an _ipv6_ prefix,
prefix length of individual subnets is assumed to be /64.

Legacy setup migration
----------------------
While building the addressing pools the **setup** routine uses legacy
parameters when the corresponding addressing parameteres are missing:

* _loopback_ default is used to create _loopback_ pool
* _lan_ and _lan_subnet_ defaults are used to create _LAN_ pool
* _p2p_ and _p2p_subnet_ defaults are used to create _p2p_ pool
'''

import sys
import typing

import netaddr
from box import Box

# Related modules
from . import common

def setup_pools(addrs: typing.Optional[Box] = None, defaults: typing.Optional[Box] = None) -> Box:
  if not addrs:
    addrs = Box({})
  if not defaults:
    defaults = Box({})
  legacy = Box({},default_box=True)

  legacy.lan = { 'ipv4': defaults.get('lan','10.0.0.0/16'), 'prefix': defaults.get('lan_subnet',24) }
  if not 'lan' in defaults and not 'lan' in addrs:
    legacy['lan']['start'] = 1
  legacy.loopback = { 'ipv4': (defaults.get('loopback','10.0.0.%d') % 0) + '/24', 'prefix': 32 }
  legacy.p2p = { 'ipv4': defaults.get('p2p','10.2.0.0/16'), 'prefix': defaults.get('p2p_subnet',30) }
  legacy.mgmt = Box({},default_box=True)

  if 'mgmt_ip' in defaults:
    legacy.mgmt.ipv4 = defaults.get('mgmt_ip') % 0
    legacy.mgmt.prefix = 24
  if 'mgmt_mac' in defaults:
    legacy.mgmt.mac = defaults.get('mgmt_mac') % 0

  addrs = legacy + addrs

  # Replace string pool definitions with data structures
  for pool,pfx in addrs.items():
    if not isinstance(pfx,dict):
      addrs[pool] = { 'ipv4': pfx, 'prefix': 32 if 'loopback' in pool else 24 }
    for af in 'ipv4','ipv6':
      if af in addrs[pool] and not addrs[pool][af]:
        del addrs[pool][af]

  return addrs

def validate_pools(addrs: typing.Optional[Box] = None) -> None:
  if not addrs:
    addrs = Box({})
  for k in ('lan','loopback'):
    if not k in addrs:
      common.error( \
        "'%s' addressing pool is missing" % k, \
        category=common.MissingValue,module='addressing')

  if isinstance(addrs.mgmt,dict):
    addrs.mgmt.setdefault('prefix',24)

  for pool,pfx in addrs.items():
    for k in ('ipv4','ipv6'):
      if k in pfx:
        try:
          network = netaddr.IPNetwork(pfx[k])
          addrs[pool][k+'_pfx'] = network
        except:
          common.error( \
            "%s prefix %s in addressing pool '%s' is invalid (%s)" % (k,pfx[k],pool,sys.exc_info()[1]), \
            category=common.IncorrectValue,module='addressing')
          continue

    if 'mac' in pfx:
      try:
        addrs[pool].mac_eui = netaddr.EUI(pfx.mac)
      except:
        common.error( \
          "MAC prefix %s in addressing pool '%s' is invalid (%s)" % (pfx.mac,pool,sys.exc_info()[1]), \
          category=common.IncorrectValue,module='addressing')
        continue

    if 'unnumbered' in pfx:
      p_type = pfx.get('type',None)
      if p_type and p_type != 'p2p':
        common.error( \
          "Unnumbered pools are by definition P2P links: %s" % pool, \
          category=common.IncorrectValue,module='addressing')
      else:
        pfx['type'] = 'p2p'
    else:
      if not 'ipv4' in pfx and not 'ipv6' in pfx:
        common.error( \
          "Addressing pool '%s' has no IPv4 or IPv6 address prefix" % pool, \
          category=common.MissingValue,module='addressing')

    if 'ipv4' in pfx and pool != 'mgmt':
      if not 'prefix' in pfx:
        common.error( \
          "IPv4 prefix length is missing in '%s' addressing pool" % pool,
          category=common.MissingValue,module='addressing')
      else:
        if not isinstance(pfx['prefix'],int):
          common.error( \
            "IPv4 prefix length in '%s' addressing pool is not an integer" % pool, \
            category=common.IncorrectValue,module='addressing')
        else:
          if pfx.prefix > 32 or pfx.prefix < 1:
            common.error( \
              "IPv4 subnet prefix length in '%s' addressing pool is not between 1 and 32" % pool, \
              category=common.IncorrectValue,module='addressing')
          if pfx.prefix <= pfx.ipv4_pfx.prefixlen:
            common.error( \
              "IPv4 subnet prefix length in '%s' addressing pool is not longer than pool prefix" % pool, \
              category=common.IncorrectValue,module='addressing')

    if 'ipv6' in pfx and 'ipv6_pfx' in pfx:
      if pfx.ipv6_pfx.prefixlen > 56:
        common.error( \
          "Error in '%s' addressing pool: IPv6 pool prefix cannot be longer than /56" % pool, \
          category=common.IncorrectValue,module='addressing')

def create_pool_generators(addrs: typing.Optional[Box] = None) -> typing.Dict:
  if not addrs:
    addrs = Box({})
  gen: typing.Dict = {}
  for pool,pfx in addrs.items():
    gen[pool] = {}
    if 'unnumbered' in pfx:
      gen[pool]['unnumbered'] = True
    for key,data in pfx.items():
      if "_pfx" in key:
        af   = key.replace('_pfx','')
        plen = pfx['prefix'] if af == 'ipv4' else 64
        gen[pool][af] = data.subnet(plen)
        if (af == 'ipv4' and plen == 32) or (pool == 'loopback'):
          next(gen[pool][af])
  return gen

def get_pool(pools: Box, pool_list: typing.List[str]) -> typing.Optional[str]:
  for p in pool_list:
    if p in pools:
      return p

  common.error( \
    'Cannot get addressing for any of these pools: %s' % str(pool_list), \
    category=common.MissingValue,module='addressing')
  return None

def get_pool_prefix(pools: typing.Dict, p: str) -> typing.Dict:
  prefixes: typing.Dict = {}
  if pools[p].get('unnumbered'):
    return prefixes
  for af in pools[p]:
    prefixes[af] = next(pools[p][af])
  return prefixes

def get(pools: Box, pool_list: typing.Optional[typing.List[str]] = None) -> typing.Dict:
  if not pool_list:
    pool_list = ['lan']
  p = get_pool(pools,pool_list)
  if p:
    return get_pool_prefix(pools,p)
  else:
    return {}

def setup(topo: Box, defaults: Box) -> None:
  common.null_to_string(topo.addressing)
  addrs = setup_pools(defaults.addressing + topo.addressing,defaults)

  common.print_verbose("Addressing\n=================")
  common.print_verbose(addrs.to_yaml())

  validate_pools(addrs)
  common.exit_on_error()

  topo.pools = create_pool_generators(addrs)
  topo.addressing = addrs
  common.exit_on_error()

def normalize_af(af: str) -> str:
  return 'ipv4' if af == 'ip' else af

def parse_prefix(prefix: str) -> typing.Dict:
  supported_af = ['ip','ipv4','ipv6']
  prefix_list: typing.Dict = {}
  if isinstance(prefix,dict):
    for af,pfx in prefix.items():
      if not af in supported_af:
        common.error( \
          'Unknown address family %s in prefix %s' % (af,prefix), \
          category=common.IncorrectValue,module='addressing')
      else:
        prefix_list[af] = netaddr.IPNetwork(pfx)
    return prefix_list
  else:
    return { 'ipv4' : netaddr.IPNetwork(prefix) }

def get_addr_mask(pfx: netaddr.IPNetwork, host: int) -> str:
  host_ip = netaddr.IPNetwork(pfx[host])
  host_ip.prefixlen = pfx.prefixlen
  return str(host_ip)
