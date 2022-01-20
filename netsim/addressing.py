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

def normalize_prefix(pfx: typing.Union[str,Box]) -> Box:
  if not pfx:
    return Box({},default_box=True,box_dots=True)
  if not isinstance(pfx,dict):
    return Box({ 'ipv4': str(pfx)},default_box=True,box_dots=True)
  for af in 'ipv4','ipv6':
    if af in pfx:
      if not pfx[af] or 'unnumbered' in pfx:
        del pfx[af]

  return pfx

def setup_pools(addr_pools: typing.Optional[Box] = None, defaults: typing.Optional[Box] = None) -> Box:
  addrs = addr_pools or Box({},default_box=True)
  defaults = defaults or Box({},default_box=True)
  legacy = Box({},default_box=True)

  legacy.lan = { 'ipv4': defaults.get('lan','10.0.0.0/16'), 'prefix': defaults.get('lan_subnet',24) }
  if not 'lan' in defaults and not 'lan' in addrs:
    legacy['lan']['start'] = 1
  legacy.loopback = { 'ipv4': (defaults.get('loopback','10.0.0.%d') % 0) + '/24', 'prefix': 32 }
  legacy.p2p = { 'ipv4': defaults.get('p2p','10.2.0.0/16'), 'prefix': defaults.get('p2p_subnet',30) }

  addrs = legacy + addrs

  # Replace string pool definitions with data structures
  for pool in list(addrs):
    clean_pfx = normalize_prefix(addrs[pool])
    if 'ipv4' in clean_pfx and not 'prefix' in clean_pfx:
      clean_pfx.prefix = 32 if 'loopback' in pool else 24
    addrs[pool] = clean_pfx

  return addrs

def validate_pools(addrs: typing.Optional[Box] = None) -> None:
  if not addrs:       # pragma: no cover (pretty hard not to have address pools)
    addrs = Box({})
  for k in ('lan','loopback'):
    if not k in addrs:          # pragma: no cover (lan and loopback pools are always created in setup_pools)
      common.error(
        "'%s' addressing pool is missing" % k,
        category=common.MissingValue,
        module='addressing')

  if isinstance(addrs.mgmt,dict):
    if not 'prefix' in addrs.mgmt:
      addrs.mgmt['prefix'] = 24

  for pool,pfx in addrs.items():
    if 'unnumbered' in pfx:
      if 'ipv4' in pfx or 'ipv6' in pfx:    # pragma: no cover -- ipv4/ipv6 prefixes have already been removed from unnumbered pools
        common.error(
          f'Pool {pool} is an unnumbered pool and cannot have IPv4 or IPv6 prefixes {pfx}',
          category=common.IncorrectValue,
          module='addressing')
        continue
    for k in ('ipv4','ipv6'):
      if k in pfx:
        if not isinstance(pfx[k],bool):
          try:
            network = netaddr.IPNetwork(pfx[k])
            addrs[pool][k+'_pfx'] = network
          except:
            common.error(
              "%s prefix %s in addressing pool '%s' is invalid (%s)" % (k,pfx[k],pool,sys.exc_info()[1]),
              category=common.IncorrectValue,
              module='addressing')
            continue

    if 'mac' in pfx:
      try:
        addrs[pool].mac_eui = netaddr.EUI(pfx.mac)
      except:
        common.error(
          "MAC prefix %s in addressing pool '%s' is invalid (%s)" % (pfx.mac,pool,sys.exc_info()[1]),
          category=common.IncorrectValue,
          module='addressing')
        continue

    if 'ipv4' in pfx and 'ipv4_pfx' in pfx and pool != 'mgmt':
      if not 'prefix' in pfx:   # pragma: no cover -- default prefix was already set to /24
        common.error(
          "IPv4 prefix length is missing in '%s' addressing pool" % pool,
          category=common.MissingValue,
          module='addressing')
      else:
        if not isinstance(pfx['prefix'],int):
          common.error(
            "IPv4 prefix length in '%s' addressing pool is not an integer" % pool,
            category=common.IncorrectValue,
            module='addressing')
        else:
          if pfx.prefix > 32 or pfx.prefix < 1:
            common.error(
              "IPv4 subnet prefix length in '%s' addressing pool is not between 1 and 32" % pool,
              category=common.IncorrectValue,
              module='addressing')
          if pfx.prefix < pfx.ipv4_pfx.prefixlen:
            common.error(
              "IPv4 subnet prefix length in '%s' addressing pool is not longer than pool prefix" % pool,
              category=common.IncorrectValue,
              module='addressing')

    if 'ipv6' in pfx and 'ipv6_pfx' in pfx:
      if pfx.ipv6_pfx.prefixlen > 56:
        common.error(
          "Error in '%s' addressing pool: IPv6 pool prefix cannot be longer than /56" % pool,
          category=common.IncorrectValue,
          module='addressing')

  if not 'ipv4' in addrs.loopback and not 'ipv6' in addrs.loopback:
    common.error(
      "Loopback addressing pool has no IPv4 or IPv6 address prefix",
      category=common.MissingValue,
      module='addressing')

def create_pool_generators(addrs: typing.Optional[Box] = None) -> typing.Dict:
  if not addrs:       # pragma: no cover (pretty hard not to have address pools)
    addrs = Box({})
  gen: typing.Dict = {}
  for pool,pfx in addrs.items():
    gen[pool] = {}
    for key,data in pfx.items():
      if "_pfx" in key:
        af   = key.replace('_pfx','')
        plen = pfx['prefix'] if af == 'ipv4' else 64
        gen[pool][af] = data.subnet(plen)
        if (af == 'ipv4' and plen == 32) or (pool == 'loopback'):
          next(gen[pool][af])
      elif isinstance(data,bool):
        gen[pool][key] = data
  return gen

def get_pool(pools: Box, pool_list: typing.List[str]) -> typing.Optional[str]:
  for p in pool_list:
    if p in pools:
      return p

  common.error(
    f'Cannot get addressing for any of these pools: {pool_list}',
    category=common.MissingValue,
    module='addressing')                       # pragma: no cover (impossible to get here due to built-in default pools)
  return None                                  # pragma: no cover

def get_nth_subnet(n: int, subnet: netaddr.IPNetwork.subnet, cache_list: list) -> netaddr.IPNetwork:
  while len(cache_list) < n:
    cache_list.append(next(subnet))
  return cache_list[n-1]

def get_pool_prefix(pools: typing.Dict, p: str, n: typing.Optional[int] = None) -> typing.Dict:
  prefixes: typing.Dict = {}
  if pools[p].get('unnumbered'):
    return { 'unnumbered': True }
  for af in list(pools[p]):
    if not 'cache' in af:
      if isinstance(pools[p][af],bool):
        prefixes[af] = pools[p][af]
      elif n:
        subnet_cache = 'cache_%s' % af
        if not subnet_cache in pools[p]:
          pools[p][subnet_cache] = []
        try:
          prefixes[af] = get_nth_subnet(n,pools[p][af],pools[p][subnet_cache])
        except StopIteration:
          common.error(
            f'Cannot allocate {n}-th {af} element from {p} pool',
            common.IncorrectValue,
            'addressing')
      else:
        try:
          prefixes[af] = next(pools[p][af])
        except StopIteration:
          common.error(
            f'Ran out of {af} prefixes in {p} pool' +
            (' (use --debug flag to get more details)' if not common.DEBUG else ''),
            common.MissingValue,
            'addressing')

  return prefixes

def get(pools: Box, pool_list: typing.Optional[typing.List[str]] = None, n: typing.Optional[int] = None) -> typing.Dict:
  if not pool_list:
    pool_list = ['lan']                   # pragma: no cover
  p = get_pool(pools,pool_list)
  if p:
    return get_pool_prefix(pools,p,n)
  else:
    return {}                             # pragma: no cover -- can't figure out how to get here

def setup(topo: Box, defaults: Box) -> None:
  common.null_to_string(topo.addressing)
  addrs = setup_pools(defaults.addressing + topo.addressing,defaults)

  common.print_verbose("Addressing\n=================")
  common.print_verbose(addrs.to_yaml())

  validate_pools(addrs)
  common.exit_on_error()

  topo.pools = create_pool_generators(addrs)
  topo.addressing = addrs
  common.print_verbose("Pools\n=================")
  common.print_verbose(str(topo.pools))

  common.exit_on_error()

def parse_prefix(prefix: typing.Union[str,dict]) -> typing.Dict:
  if common.DEBUG:                     # pragma: no cover (debugging printout)
    print(f"parse prefix: {prefix}")
  if not prefix:
    return {}
  supported_af = ['ip','ipv4','ipv6']
  prefix_list: typing.Dict = {}
  if isinstance(prefix,dict):
    for af,pfx in prefix.items():
      if not af in supported_af:
        common.error( \
          'Unknown address family %s in prefix %s' % (af,prefix), \
          category=common.IncorrectValue,module='addressing')
      else:
        if isinstance(pfx,bool):
          prefix_list[af] = pfx
        else:
          try:
            prefix_list[af] = netaddr.IPNetwork(pfx)
          except Exception as ex:
            common.error(f'Cannot parse {af} prefix: {prefix}\n... {ex}',common.IncorrectValue,'addressing')
            return {}
          if str(prefix_list[af]) != str(prefix_list[af].cidr):
            common.error(f'{af} prefix contains host bits: {prefix}',common.IncorrectValue,'addressing')
    return prefix_list
  else:
    return { 'ipv4' : netaddr.IPNetwork(prefix) }

def get_addr_mask(pfx: netaddr.IPNetwork, host: int) -> str:
  host_ip = netaddr.IPNetwork(pfx[host])
  host_ip.prefixlen = pfx.prefixlen
  return str(host_ip)
