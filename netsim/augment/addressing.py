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
prefix length of individual subnets is assumed to be /64 unless the
pool has _prefix6_ attribute.

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
import types

import netaddr
from box import Box

# Related modules
from ..data import get_empty_box,get_box,null_to_string
from ..data.validate import validate_attributes
from ..utils import log,strings

def normalize_prefix(pfx: typing.Union[str,Box]) -> Box:

  # Normalize IP addr strings, e.g. 2001:001::/48 becomes 2001:1::/48
  def normalize_ip(ip:typing.Union[str,bool]) -> typing.Union[str,bool]:
    try:
      return str(netaddr.IPNetwork(ip)) if isinstance(ip,str) else ip
    except Exception as ex:
      log.error(
        f'Cannot parse address prefix: {ex}',
        log.IncorrectValue,
        'addressing')
      return False

  if not pfx:
    return get_empty_box()
  if not isinstance(pfx,dict):
    return get_box({ 'ipv4': normalize_ip(pfx) })
  for af in 'ipv4','ipv6':
    if af in pfx:
      if not pfx[af] or 'unnumbered' in pfx:  # If 'unnumbered' is set, ipv4/ipv6 will be based on loopback afs (per node)
        del pfx[af]
      else:
        pfx[af] = normalize_ip(pfx[af])

  return pfx

def rebuild_prefix(pfx: typing.Union[dict,Box]) -> Box:
  out_pfx = get_empty_box()
  for af in ('ipv4','ipv6'):
    if af in pfx:
      out_pfx[af] = str(pfx[af]) if not isinstance(pfx[af],bool) else pfx[af]
  return out_pfx

def setup_pools(addr_pools: typing.Optional[Box] = None, defaults: typing.Optional[Box] = None) -> Box:
  addrs = addr_pools or get_empty_box()
  defaults = defaults or get_empty_box()
  legacy = get_empty_box()

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

def validate_pools(addrs: Box, topology: Box) -> None:
  for p_name,p_value in addrs.items():
    validate_attributes(
      data=p_value,                                   # Validate node data
      topology=topology,
      data_path=f'addressing.{p_name}',               # Topology path to node name
      data_name=f'address pool',
      attr_list=['pool'],                             # We're checking address pool attributes
      modules=[],                                     # No module attributes in pools yet
#      modules=n_data.get('module',[]),                # ... against node modules
      module='addressing')

  if not addrs:       # pragma: no cover (pretty hard not to have address pools)
    addrs = get_empty_box()
  for k in ('lan','loopback'):
    if not k in addrs:          # pragma: no cover (lan and loopback pools are always created in setup_pools)
      log.error(
        "'%s' addressing pool is missing" % k,
        category=log.MissingValue,
        module='addressing')

  if isinstance(addrs.mgmt,dict):
    if not 'prefix' in addrs.mgmt:
      addrs.mgmt['prefix'] = 24

  for pool,pfx in addrs.items():
    if 'unnumbered' in pfx:
      if 'ipv4' in pfx or 'ipv6' in pfx:    # pragma: no cover -- ipv4/ipv6 prefixes have already been removed from unnumbered pools
        log.error(
          f'Pool {pool} is an unnumbered pool and cannot have IPv4 or IPv6 prefixes {pfx}',
          category=log.IncorrectValue,
          module='addressing')
        continue
    for k in ('ipv4','ipv6'):
      if k in pfx:
        if not isinstance(pfx[k],bool):
          try:
            network = netaddr.IPNetwork(pfx[k])
            if str(network.cidr) != pfx[k]:
              log.error( f"pool '{pool}' is using an invalid prefix {pfx[k]} with host bits set ({str(network.cidr)})",
                            category=log.IncorrectValue, module='addressing')
            addrs[pool][k+'_pfx'] = network
          except:
            log.error(
              "%s prefix %s in addressing pool '%s' is invalid (%s)" % (k,pfx[k],pool,sys.exc_info()[1]),
              category=log.IncorrectValue,
              module='addressing')
            continue

    if 'mac' in pfx:
      try:
        addrs[pool].mac_eui = netaddr.EUI(pfx.mac)
      except:
        log.error(
          "MAC prefix %s in addressing pool '%s' is invalid (%s)" % (pfx.mac,pool,sys.exc_info()[1]),
          category=log.IncorrectValue,
          module='addressing')
        continue

    if 'ipv4' in pfx and 'ipv4_pfx' in pfx and pool != 'mgmt':
      if not 'prefix' in pfx:   # pragma: no cover -- default prefix was already set to /24
        log.error(
          "IPv4 prefix length is missing in '%s' addressing pool" % pool,
          category=log.MissingValue,
          module='addressing')
      else:
        if not isinstance(pfx['prefix'],int):
          log.error(
            "IPv4 prefix length in '%s' addressing pool is not an integer" % pool,
            category=log.IncorrectValue,
            module='addressing')
        else:
          if pfx.prefix > 32 or pfx.prefix < 1:
            log.error(
              "IPv4 subnet prefix length in '%s' addressing pool is not between 1 and 32" % pool,
              category=log.IncorrectValue,
              module='addressing')
          if pfx.prefix < pfx.ipv4_pfx.prefixlen:
            log.error(
              "IPv4 subnet prefix length in '%s' addressing pool is not longer than pool prefix" % pool,
              category=log.IncorrectValue,
              module='addressing')

    if 'ipv6' in pfx and 'ipv6_pfx' in pfx:
      if pfx.ipv6_pfx.prefixlen > 56:
        log.error(
          "Error in '%s' addressing pool: IPv6 pool prefix cannot be longer than /56" % pool,
          category=log.IncorrectValue,
          module='addressing')

  if not 'ipv4' in addrs.loopback and not 'ipv6' in addrs.loopback:
    log.error(
      "Loopback addressing pool has no IPv4 or IPv6 address prefix",
      category=log.MissingValue,
      module='addressing')

def create_pool_generators(addrs: Box, no_copy_list: list) -> Box:
  if not addrs:       # pragma: no cover (pretty hard not to have address pools)
    addrs = get_empty_box()
  gen = get_empty_box()
  for pool,pfx in addrs.items():
    gen[pool] = {}
    for key,data in pfx.items():
      if "_pfx" in key:
        af   = key.replace('_pfx','')
        plen = pfx['prefix'] if af == 'ipv4' else pfx.get('prefix6',64)
        gen[pool][af] = data.subnet(plen)
        if (af == 'ipv4' and plen == 32) or (af == 'ipv6' and plen >= 127) or (pool == 'loopback'):
          next(gen[pool][af])
      elif not key in no_copy_list:
        gen[pool][key] = data
  return gen

def get_pool(pools: Box, pool_list: typing.List[str]) -> typing.Optional[str]:
  for p in pool_list:
    if p in pools:
      return p

  log.error(
    f'Cannot get addressing for any of these pools: {pool_list}',
    category=log.MissingValue,
    module='addressing')                       # pragma: no cover (impossible to get here due to built-in default pools)
  return None                                  # pragma: no cover

def get_nth_subnet(n: int, subnet: netaddr.IPNetwork.subnet, cache_list: list) -> netaddr.IPNetwork:
  while len(cache_list) < n:
    cache_list.append(next(subnet))
  return cache_list[n-1]

def get_pool_prefix(pools: Box, p: str, n: typing.Optional[int] = None) -> Box:
  prefixes = get_empty_box()
  for af in list(pools[p]):
    if 'cache' in af:                                                 # Skipping over caches
      continue
    if not isinstance(pools[p][af],types.GeneratorType):              # Copy non-generator attributes
      prefixes[af] = pools[p][af]
      continue

    if n:                                                             # Allocating a specific prefix or IP address from a subnet
      subnet_cache = 'cache_%s' % af
      if not subnet_cache in pools[p]:                                # Set up a cache to speed up things
        pools[p][subnet_cache] = []
      try:
        prefixes[af] = get_nth_subnet(n,pools[p][af],pools[p][subnet_cache])
      except StopIteration:
        log.error(
          f'Cannot allocate {n}-th {af} element from {p} pool',
          log.IncorrectValue,
          'addressing')
    else:                                                             # Just asking for the next available prefix
      try:
        prefixes[af] = next(pools[p][af])                             # Let's see if we can get one more
      except StopIteration:                                           # Ouch, ran out of prefixes, report that
        log.error(
          f'Ran out of {af} prefixes in {p} pool' +
          (' (use --debug addr CLI argument to get more details)' if not log.debug_active('addr') else ''),
          log.MissingValue,
          'addressing')

  if log.debug_active('addressing'):
    print(f'get_pool_prefix: {p} => {prefixes}')
  return prefixes

def get(pools: Box, pool_list: typing.Optional[typing.List[str]] = None, n: typing.Optional[int] = None) -> Box:
  if not pool_list:
    pool_list = ['lan']                   # pragma: no cover
  p = get_pool(pools,pool_list)
  if p:
    return get_pool_prefix(pools,p,n)
  else:
    return get_empty_box()                # pragma: no cover -- can't figure out how to get here

def setup(topology: Box) -> None:
  defaults = topology.defaults
  null_to_string(topology.addressing)
  addrs = setup_pools(defaults.addressing + topology.addressing,defaults)

  if log.debug_active('addressing'):
    print("addressing:")
    strings.print_structured_dict(addrs,'.. ')

  validate_pools(addrs,topology)
  log.exit_on_error()

  topology.pools = create_pool_generators(addrs,defaults.attributes.pool_no_copy)
  topology.addressing = addrs

  if log.debug_active('addressing'):
    print("pools:")
    strings.print_structured_dict(topology.pools,'.. ')

  log.exit_on_error()

def parse_prefix(prefix: typing.Union[str,Box]) -> Box:
  if log.debug_active('addr'):                     # pragma: no cover (debugging printout)
    print(f"parse prefix: {prefix} type={type(prefix)}")

  empty_box = get_empty_box()
  if not prefix:
    return empty_box

  supported_af = ['ipv4','ipv6']
  prefix_list = get_empty_box()
  if not isinstance(prefix,Box):
    return get_box({ 'ipv4' : netaddr.IPNetwork(prefix) })

  if 'ip' in prefix:                                  # Deal with legacy 'ip' address family -- rename it to ipv4
    if 'ipv4' in prefix:
      log.error( \
        f'Cannot have IP and IPv4 address families in prefix {prefix}',
        category=log.IncorrectValue,
        module='addressing')
      return empty_box

    prefix.ipv4 = prefix.ip
    prefix.pop('ip',None)

  for af,pfx in prefix.items():
    if not af in supported_af:                        # Are we dealing with an address family prefix?
      prefix_list[af] = pfx                           # No, copy attribute over, someone should have checked it beforehand
      continue

    if isinstance(pfx,bool):
      prefix_list[af] = pfx
      continue

    try:
      prefix_list[af] = netaddr.IPNetwork(pfx)
    except Exception as ex:
      log.error(f'Cannot parse {af} prefix: {prefix}\n... {ex}',log.IncorrectValue,'addressing')
      return empty_box
    if str(prefix_list[af]) != str(prefix_list[af].cidr):
      log.error(f'{af} prefix contains host bits: {prefix}',log.IncorrectValue,'addressing')    

  return prefix_list

def get_addr_mask(pfx: netaddr.IPNetwork, host: int) -> str:
  host_ip = netaddr.IPNetwork(pfx[host])
  host_ip.prefixlen = pfx.prefixlen
  return str(host_ip)
