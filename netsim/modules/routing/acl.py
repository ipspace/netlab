#
# Generic routing module -- ACL
#

import typing
from dataclasses import dataclass

from box import Box

from netsim.utils import log

from ...data import append_to_list, get_box
from .normalize import check_routing_object, import_routing_object


def expand_acl_address_entry(p_entry: Box, topology: Box) -> Box:
  """
  expand_acl_address_entry:
  * Transform 'pool' and 'prefix' keywords into 'ipv4' and 'ipv6'
  * Resolve node-inteface and node-role tuples into 'ipv4' and 'ipv6'
  """

  def add_acl_prefixes(p_entry: Box, data: Box) -> None:
    for af in log.AF_LIST:
      if af in data and isinstance(data[af],str):
        append_to_list(p_entry,af,data[af])

  for p_name in p_entry.get('pool',[]):
    add_acl_prefixes(p_entry,topology.addressing[p_name])

  for p_name in p_entry.get('prefix',[]):
    add_acl_prefixes(p_entry,topology.prefix[p_name])

  for node_name in p_entry.get('node',[]):
    node_data = topology.nodes[node_name]
    intf_list = node_data.get("interfaces", [])
    if 'loopback' in node_data:
      intf_list += [ node_data.loopback ]

    if "interface" in p_entry:
      ifname = p_entry.interface
      intf_list = [intf for intf in intf_list if intf.get("ifname") in ifname]
      if not intf_list:
        log.error(f"Node {node_name} has no interface {ifname} referenced in ACL entry", log.IncorrectValue, "acl")
        continue
    elif "role" in p_entry:
      role = p_entry.role
      match = [intf for intf in intf_list if intf.get("role") in role]
      if not match:
        log.error(
          f"Node {node_name} has no interface with role {role} referenced in ACL entry",
          log.IncorrectValue,
          "acl")
        continue

    for intf in intf_list:
      add_acl_prefixes(p_entry,intf)

  for kw in ('pool','prefix','node','interface','role'):
    p_entry.pop(kw,None)

  return p_entry


def resolve_protocol(p_protocol: typing.Union[str, int]) -> int:
  protocol_number = {
    "icmp": 1,
    "ip": 4,
    "tcp": 6,
    "udp": 17,
    "ipv6": 41,
    "esp": 50,
    "ahp": 51,
  }

  if isinstance(p_protocol, int):
    return p_protocol

  if isinstance(p_protocol, str):
    if p_protocol not in protocol_number:
      log.fatal(
        f"Unknown protocol {p_protocol}. Please update resolve_protocol() if data model changed",
      )
    return protocol_number[p_protocol]


@dataclass
class validation_context:
  p_name: str
  idx: int
  af_ipv4: bool
  protocol: int
  established: bool


def validate_acl_address_entry(p_entry: Box, ctx: validation_context) -> None:

  UDP = 17
  TCP = 6

  if ctx.protocol < 0 or ctx.protocol > 255:
    log.error(
      f"ACL {ctx.p_name} entry {ctx.idx} protocol number out of IANA range [0,255]",
      category=log.IncorrectAttr,
    )

  if ctx.established and ctx.protocol != TCP:
    log.error(
      f"ACL {ctx.p_name} entry {ctx.idx} established keyword is only valid with TCP protocol",
      category=log.IncorrectAttr,
    )

  # By this time we should have a valid ipv4 address acl_address, either
  # by user input or synthesized from prefix / pool or node/interface
  # node/role tuples. Valdiation has been run for all those objects
  # so hopefully the adress is valid.

  for direction in ("src", "dst"):
    entry = p_entry[direction]
    if 'port' in entry and ctx.protocol not in (TCP, UDP):
      log.error(
        f"ACL {ctx.p_name} entry {ctx.idx} cannot use a port or "
        f"port range in {direction} address with this protocol. Use UDP/TCP",
        category=log.IncorrectAttr,
      )
      continue

    # Convert "not in" into a combination of "gt"/"lt"
    if 'port.not_in' in entry:
      port_list = sorted(entry.port.not_in)
      entry.port.lt = port_list[0]
      entry.port.gt = port_list[1]
      entry.port.pop('not_in')


def expand_acl(p_name: str, o_name: str, node: Box, topology: Box) -> typing.Optional[list]:
  ctx = validation_context(p_name=p_name, idx=0, af_ipv4=True, protocol=0, established=False)
  acl_list = node.routing[o_name][p_name]
  for idx, entry in enumerate(list(acl_list)):
    ctx.protocol = resolve_protocol(entry.protocol)
    ctx.established = entry.get("established", False)
    ctx.idx = idx
    for addr_key in ("src", "dst"):
      if addr_key in entry:
        entry[addr_key] = expand_acl_address_entry(entry[addr_key], topology)
    validate_acl_address_entry(entry, ctx)
    acl_list[idx] = entry

  acl_list.sort(key=lambda e: e.get("sequence", 10))
  return None


def expand_af_acl(acl_list: list,acl_af: str, acl_name: str, node_name: str) -> list:
  """
  Expands the ACL entries for a single address family. Lists of source/
  destination IP addresses are expanded as a cartesian product
  """
  if not acl_list:                                          # Nothing to do 
    return acl_list

  acl_sequence = 100
  acl_result: list = []

  def get_port_op(direction: str, port_op: str, port_value: typing.Union[int,list]) -> dict:
    if port_op == 'none':
      return {}

    port_data: dict = {
      'port_op' : port_op
    }
    if isinstance(port_value,list):
      port_value = sorted(port_value)
      port_data['port_range'] = { 'min': port_value[0], 'max': port_value[1] }
    else:
      port_data['port'] = port_value
    return { direction: port_data }

  def generate_acl_items(acl_data: Box, src_port: Box, dst_port: Box) -> None:
    """
    Add port information to ACL entry with SRC/DST addresses. Iterate over all
    port qualifiers, and over all port values (but only for "eq" condition)
    """
    nonlocal acl_sequence, acl_result

    for s_port_op, s_port in src_port.items():
      for s_port_n in s_port if s_port_op == 'eq' else [ s_port ]:
        acl_sp_item = acl_data + get_port_op('src',s_port_op,s_port_n)
        for d_port_op, d_port in dst_port.items():
          for d_port_n in d_port if d_port_op == 'eq' else [ d_port ]:
            acl_final = acl_sp_item + get_port_op('dst',d_port_op,d_port_n)
            acl_final.sequence = acl_sequence
            acl_result.append(acl_final)
            acl_sequence += 10

  for acl_idx,acl_entry in enumerate(acl_list,1):           # Iterate over all ACL entries
    src_list = acl_entry.src.get(acl_af,[])                 # Get source/destination AF-specific entries
    dst_list = acl_entry.dst.get(acl_af,[])
    acl_data = get_box({ k:v for k,v in acl_entry.items() if k not in ['src','dst'] })
    src_port = acl_entry.src.get('port',{'none': 0 })
    dst_port = acl_entry.dst.get('port',{'none': 0 })

    if not src_list and not dst_list:                       # No usable AF entries? Move on...
      continue
    if not src_list or not dst_list:                        # Otherwise we need both source and destination entries
      log.warning(
        text=f'ACL {acl_name}[{acl_idx}] on node {node_name} does not have {acl_af} entries in source and destination fields',
        flag='acl_af_src_dst',module='routing')
      continue

    if 'description' in acl_data:
      acl_result.append(get_box({'description': acl_data.description, 'sequence': acl_sequence}))
      acl_sequence += 10
      acl_data.pop('description',None)

    for src_ip in src_list:
      for dst_ip in dst_list:
        acl_item = acl_data + {'src': { acl_af: src_ip }} + {'dst': { acl_af: dst_ip }}
        for kw in ['src','dst']:
          if '/' not in acl_item[kw][acl_af]:
            acl_item[kw].host = True
          if acl_item[kw][acl_af].endswith('/0'):
            acl_item[kw].any = True

        generate_acl_items(acl_item,src_port,dst_port)

  return acl_result

#
# Entry points:
#
# - interface_acl_references is called to trigger import of ACLs used on interfaces
# - create_af_acls is called during the cleanup phase to create per-AF ACLs
#

def interface_acl_references(node: Box,topology: Box) -> None:
  """
  Ensure ACLs referenced on interfaces are merged at node level. This needs to
  be called early in post-transform, before ACLs are processed at node level.
  """
  for intf in node.get("interfaces",[]):
    intf_acl = intf.get("routing.acl",{})
    if not intf_acl:
      continue
    for acl_dir,acl_data in intf_acl.items():
      if isinstance(acl_data,str):
        intf.routing.acl[acl_dir] = { acl_af: acl_data for acl_af in log.AF_LIST if acl_af in intf }
        acl_list = [ acl_data ]
      else:
        acl_list = acl_data.values()
      for acl_name in acl_list:
        if import_routing_object(acl_name,'acl',node,topology):
          check_routing_object(acl_name,'acl',node,topology)


def create_af_acls(node_pdata: Box,o_type: str,node: Box,topology: Box) -> None:
  """
  Create per-AF node ACLs
  """
  node_af_list = node.get('af',{}).keys() or log.AF_LIST
  for acl_name,acl_list in node_pdata.items():
    for acl_af in node_af_list:
      acl_data = expand_af_acl(acl_list,acl_af,acl_name,node.name)
      node.routing['_'+o_type][acl_af][acl_name] = acl_data
