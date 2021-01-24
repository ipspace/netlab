'''
Set up network addressing
=========================

The network model needs three types of addressing pools:

* Loopback addresses
* P2P addresses
* LAN and stub link addresses

Each pool could have IPv4 and IPv6 component.

Notes:
* _lan_ pool is used for stub and P2P prefixes if the corresponding
  pools are not defined

The addressing pools are set up in _addressing_ part of model
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

import netaddr
import common
import os
import yaml
import sys

def setup_pools(addrs = {},defaults = {}):
  legacy = {}

  legacy['lan'] = { 'ipv4': defaults.get('lan','10.0.0.0/16'), 'prefix': defaults.get('lan_subnet',24) }
  if not 'lan' in defaults and not 'lan' in addrs:
    legacy['lan']['start'] = 1
  legacy['loopback'] = { 'ipv4': (defaults.get('loopback','10.0.0.%d') % 0) + '/24', 'prefix': 32 }
  legacy['p2p'] = { 'ipv4': defaults.get('p2p','10.2.0.0/16'), 'prefix': defaults.get('p2p_subnet',30) }
  legacy['mgmt'] = {}

  if 'mgmt_ip' in defaults:
    legacy['mgmt']['ipv4'] = defaults.get('mgmt_ip') % 0
    legacy['mgmt']['prefix'] = 24
  if 'mgmt_mac' in defaults:
    legacy['mgmt']['mac'] = defaults.get('mgmt_mac') % 0

  addrs = common.merge_defaults(addrs,legacy)

  # Replace string pool definitions with data structures
  for pool,pfx in addrs.items():
    if not isinstance(pfx,dict):
      addrs[pool] = { 'ipv4': pfx, 'prefix': 32 if 'loopback' in pool else 24 }
    for af in 'ipv4','ipv6':
      if af in addrs[pool] and addrs[pool][af] is None:
        del addrs[pool][af]

  return addrs

def validate_pools(addrs = {}):
  for k in ('lan','loopback'):
    if not k in addrs:
      common.error("'%s' addressing pool is missing" % k)

  if 'mgmt' in addrs:
    addrs['mgmt']['prefix'] = addrs['mgmt'].get('prefix',24)

  for pool,pfx in addrs.items():
    for k in ('ipv4','ipv6'):
      if k in pfx:
        try:
          network = netaddr.IPNetwork(pfx[k])
          pfx[k+'_pfx'] = network
        except:
          common.error("%s prefix %s in addressing pool '%s' is invalid (%s)" % (k,pfx[k],pool,sys.exc_info()[1]))
          continue

    if 'mac' in pfx:
      try:
        pfx['mac_eui'] = netaddr.EUI(pfx['mac'])
      except:
        common.error("MAC prefix %s in addressing pool '%s' is invalid (%s)" % (pfx['mac'],pool,sys.exc_info()[1]))
        continue

    if not 'ipv4' in pfx and not 'ipv6' in pfx:
      common.error("Addressing pool '%s' has no IPv4 or IPv6 address prefix" % pool)

    if 'ipv4' in pfx and pool != 'mgmt':
      if not 'prefix' in pfx:
        common.error("IPv4 prefix length is missing in '%s' addressing pool" % pool)
      else:
        if not isinstance(pfx['prefix'],int):
          common.error("IPv4 prefix length in '%s' addressing pool is not an integer" % pool)
        else:
          if pfx['prefix'] > 32 or pfx['prefix'] < 1:
            common.error("IPv4 subnet prefix length in '%s' addressing pool is not between 1 and 32" % pool)
          if pfx['prefix'] <= pfx['ipv4_pfx'].prefixlen:
            common.error("IPv4 subnet prefix length in '%s' addressing pool is not longer than pool prefix" % pool)

    if 'ipv6' in pfx:
      if pfx['ipv6_pfx'].prefixlen > 56:
        common.error("Error in '%s' addressing pool: IPv6 pool prefix cannot be longer than /56" % pool)

def create_pool_generators(addrs = {}):
  gen = {}
  for pool,pfx in addrs.items():
    gen[pool] = {}
    for key,data in pfx.items():
      if "_pfx" in key:
        key  = key.replace('_pfx','')
        plen = pfx['prefix'] if key == 'ipv4' else 64
        gen[pool][key] = data.subnet(plen)
        if (key == 'ipv4' and plen == 32) or (pool == 'loopback'):
          next(gen[pool][key])
  return gen

def get(pools,pool_list = ['lan']):
  prefixes = {}
  for p in pool_list:
    if p in pools:
      for af in pools[p]:
        prefixes[af] = next(pools[p][af])
      return prefixes

  common.error('Cannot get a prefix for any of these pools: ' % pool_list)
  return prefixes

def setup(topo,defaults = {}):
  addrs = topo.get('addressing',{})
  addrs = common.merge_defaults(addrs,defaults.get('addressing'))
  addrs = setup_pools(addrs,defaults)
  topo['addressing'] = addrs

  common.print_verbose("Addressing\n=================")
  common.print_verbose(yaml.dump(addrs))

  validate_pools(addrs)
  common.exit_on_error()

  topo['pools'] = create_pool_generators(addrs)
  common.exit_on_error()

def normalize_af(af):
  return 'ipv4' if af == 'ip' else af

def parse_prefix(prefix):
  supported_af = ['ip','ipv4','ipv6']
  prefix_list = {}
  if isinstance(prefix,dict):
    for af,pfx in prefix.items():
      if not af in supported_af:
        common.error('Unknown address family %s in prefix %s' % (af,prefix))
      else:
        prefix_list[af] = netaddr.IPNetwork(pfx)
    return prefix_list
  else:
    return { 'ipv4' : netaddr.IPNetwork(prefix) }

def get_addr_mask(pfx,host):
  host_ip = netaddr.IPNetwork(pfx[host])
  host_ip.prefixlen = pfx.prefixlen
  return str(host_ip)
