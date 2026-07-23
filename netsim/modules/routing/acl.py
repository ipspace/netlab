#
# Generic routing module -- ACL
#

import typing
from dataclasses import dataclass

from box import Box

from netsim.utils import log

from ...data import get_box
from .normalize import import_routing_object

"""
expand_acl_address_entry:
* Transform 'pool' and 'prefix' keywords into 'ipv4' and 'ipv6'
* Resolve node inteface and node-role tupples into 'ipv4' and 'ipv6'
"""


def expand_acl_address_entry(p_entry: Box, topology: Box) -> Box:
  extra_data = None
  if "pool" in p_entry:
    extra_data = topology.addressing[p_entry.pool]
    p_entry.pop("pool", None)

  if "prefix" in p_entry:
    extra_data = topology.prefix[p_entry.prefix]
    p_entry.pop("prefix", None)

  if "node" in p_entry:
    node_name = p_entry.node
    node_data = topology.nodes[node_name]
    intf_list = node_data.get("interfaces", [])

    if "interface" in p_entry:
      ifname = p_entry.interface
      match = [intf for intf in intf_list if intf.get("ifname") == ifname]
      if not match:
        log.error(f"Node {node_name} has no interface {ifname} referenced in ACL entry", log.IncorrectValue, "acl")
        return p_entry
      extra_data = match[0]
      p_entry.pop("interface", None)

    elif "role" in p_entry:
      role = p_entry.role
      match = [intf for intf in intf_list if intf.get("role") == role]
      if not match:
        log.error(
          f"Node {node_name} has no interface with role {role} referenced in ACL entry", log.IncorrectValue, "acl"
        )
        return p_entry
      if len(match) > 1:
        log.error(
          f"Node {node_name} has multiple interfaces with role {role}, ACL entry is ambiguous",
          log.IncorrectValue,
          "acl",
        )
        return p_entry
      extra_data = match[0]
      p_entry.pop("role", None)

    p_entry.pop("node", None)

  if extra_data:
    for af in ("ipv4", "ipv6"):
      if af in extra_data:
        p_entry[af] = extra_data[af]
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
  af = "ipv4" if ctx.af_ipv4 else "ipv6"
  port_keys = ("port", "port_range")

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
    if af not in entry and "any" not in entry:
      log.error(
        f"ACL {ctx.p_name} entry {ctx.idx} requires a valid {af}/any address in {direction} address",
        category=log.IncorrectAttr,
      )

    if any(k in entry for k in port_keys) and ctx.protocol not in (TCP, UDP):
      log.error(
        f"ACL {ctx.p_name} entry {ctx.idx} cannot use a port or "
        f"port range in {direction} address with this protocol. Use UDP/TCP",
        category=log.IncorrectAttr,
      )

    if "port_range" in entry and entry.port_range.min >= entry.port_range.max:
      log.error(
        f"ACL {ctx.p_name} entry {ctx.idx} has an invalid {direction} port range: min greater or equal to max",
        category=log.IncorrectAttr,
      )

    # get rid of port_op if we do not need it
    if not any(k in entry for k in port_keys):
      entry.pop("port_op", None)

  if any(k in p_entry.src for k in port_keys) and any(k in p_entry.dst for k in port_keys):
    log.error(
      f"ACL {ctx.p_name} entry {ctx.idx} cannot specify a port or port range in both source and destination address",
      category=log.IncorrectAttr,
    )


def expand_acl_description(entry: Box, expansion: list) -> None:
  if "description" not in entry:
    return

  description_seq = entry.get("sequence")
  entry.sequence = description_seq + 1  # the real entry moves one past it
  description_entry = get_box({"sequence": description_seq, "description": entry.pop("description")})
  expansion.append(description_entry)


def expand_acl_portop(entry: Box, node: Box, topology: Box, expansion: list) -> None:

  for addr_key in ("src", "dst"):
    addr_entry = entry.get(addr_key)
    if not addr_entry:
      continue
    port_range = addr_entry.get("port_range")
    if not port_range or addr_entry.get("port_op") != "not_in":
      continue

    port_min = port_range.min
    port_max = port_range.max

    upper_entry = get_box(entry.to_dict())
    upper_entry.sequence = entry.sequence + 1

    entry[addr_key].port = port_min
    entry[addr_key].port_op = "lt"
    entry[addr_key].pop("port_range", None)
    upper_entry[addr_key].port = port_max
    upper_entry[addr_key].port_op = "gt"
    upper_entry[addr_key].pop("port_range", None)
    expansion.append(upper_entry)
  return None


# Entry points below


def expand_acl(p_name: str, o_name: str, node: Box, topology: Box) -> typing.Optional[list]:
  ctx = validation_context(p_name=p_name, idx=0, af_ipv4=True, protocol=0, established=False)
  acl_def = node.routing[o_name][p_name]
  acl_list = acl_def.value
  ctx.af_ipv4 = acl_def.af == "ipv4"
  expansion: list = []

  for idx, entry in enumerate(list(acl_list)):
    ctx.protocol = resolve_protocol(entry.protocol)
    ctx.established = entry.get("established", False)
    ctx.idx = idx
    for addr_key in ("src", "dst"):
      if addr_key in entry:
        entry[addr_key] = expand_acl_address_entry(entry[addr_key], topology)
    validate_acl_address_entry(entry, ctx)
    # Synthesize new acl entries, when needed
    expand_acl_description(entry, expansion)
    expand_acl_portop(entry, node, topology, expansion)
    acl_list[idx] = entry

  acl_list.extend(expansion)
  acl_list.sort(key=lambda e: e.get("sequence", 10))
  return None


"""
Ensure ACLs referenced on interfaces are merged
at node level. This needs to be called early in
post-transform, before ACLs are processed at node
level.
"""


def resolve_interface_acl_references(node: Box, topology: Box) -> None:
  routing = topology.get("routing")
  if routing is None:
    return

  global_acls = routing.get("acl", {})
  node_acls = node.get("routing", {}).get("acl", {})

  for intf in node.get("interfaces", []):
    intf_acl = intf.get("routing", {}).get("acl", {})

    for direction in ("in", "out"):
      direction_acl = intf_acl.get(direction, {})

      for af in ("ipv4", "ipv6"):
        acl_id = direction_acl.get(af)
        if not acl_id:
          continue

        acl = global_acls.get(acl_id)
        if acl is None:
          log.error(
            f"Interface '{intf.ifname}' on '{node.name}' "
            f"references non-existent ACL '{acl_id}' "
            f"in 'routing.acl.{direction}.{af}'",
            category=log.IncorrectAttr,
          )
          continue

        if acl.get("af") != af:
          log.error(
            f"Interface '{intf.ifname}' on '{node.name}' "
            f"references {acl.get('af')} ACL '{acl_id}' "
            f"as {af} in 'routing.acl.{direction}.{af}'",
            category=log.IncorrectAttr,
          )
          continue

        if acl_id not in node_acls:
          import_routing_object(acl_id, "acl", node, topology)
