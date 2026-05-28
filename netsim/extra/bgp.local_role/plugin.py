import typing

from box import Box

from netsim import api, modules
from netsim.utils import log
from netsim.utils import routing as _bgp

_config_name = "bgp.local_role"
_requires = ["bgp"]
_execute_after = ["bgp.session"]

_ATTR_LIST = ["local_role", "local_role_strict"]


def _use_plugin_template(node: Box) -> bool:
  """Return False for the BIRD daemon (roles are rendered in daemons/bird/bgp.j2)."""
  return not (node.get("_daemon") and node.device == "bird")


def _check_strict_without_role(
    ndata: Box, topology: Box, intf: typing.Optional[Box] = None) -> bool:
  """Reject bgp.local_role_strict without bgp.local_role. Return True if the check passed."""
  strict = modules.get_effective_module_attribute(
    path="bgp.local_role_strict", intf=intf, node=ndata, topology=topology)
  role = modules.get_effective_module_attribute(
    path="bgp.local_role", intf=intf, node=ndata, topology=topology)
  if strict and not role:
    where = f"node {ndata.name}"
    if intf is not None:
      where += f" interface {intf.name}"
    log.error(
      f"Cannot use bgp.local_role_strict without bgp.local_role ({where})",
      category=log.IncorrectValue,
      module=_config_name,
    )
    return False
  return True


def _check_ibgp_local_role(ndata: Box, topology: Box, intf: typing.Optional[Box] = None) -> None:
  """Report an error if RFC 9234 role attributes are set on an IBGP session."""
  if not _check_strict_without_role(ndata, topology, intf):
    return
  for attr in _ATTR_LIST:
    if not modules.get_effective_module_attribute(
        path=f"bgp.{attr}", intf=intf, node=ndata, topology=topology):
      continue
    where = f"node {ndata.name}"
    if intf is not None:
      where += f" interface {intf.name}"
    log.error(
      f"Cannot use bgp.{attr} on IBGP session ({where})",
      category=log.IncorrectValue,
      module=_config_name,
    )
    return


def _check_node_ibgp_local_role(ndata: Box, topology: Box) -> None:
  """Reject node-level role attributes when the node has IBGP neighbors."""
  for _ngb in _bgp.neighbors(ndata, select=["ibgp", "localas_ibgp"]):
    _check_ibgp_local_role(ndata, topology)
    return


def apply_neighbor_attributes(node: Box, ngb: Box, intf: Box, topology: Box) -> bool:
  """Copy bgp.local_role* interface attributes to an EBGP neighbor.

  Returns:
    True if at least one attribute was applied to the neighbor.
  """
  if not _check_strict_without_role(node, topology, intf):
    return False

  values: dict[str, typing.Any] = {}
  for attr in _ATTR_LIST:
    attr_value = modules.get_effective_module_attribute(
      path=f"bgp.{attr}", intf=intf, node=node)
    if attr_value:
      values[attr] = attr_value

  if not values:
    return False

  if not _bgp.check_device_attribute_support(
      "local_role", node, ngb, topology, _config_name):
    return False

  for attr, attr_value in values.items():
    ngb[attr] = attr_value

  if _use_plugin_template(node):
    api.node_config(node, _config_name)
    _bgp.clear_bgp_session(node, ngb)

  return True


def post_transform(topology: Box) -> None:
  """Apply RFC 9234 BGP role attributes to EBGP neighbors and reject IBGP usage."""
  for ndata in topology.nodes.values():
    if "bgp" not in ndata.get("module", []):
      continue

    _bgp.cleanup_neighbor_attributes(ndata, topology, _ATTR_LIST)

    for intf, ngb in _bgp.intf_neighbors(ndata, select=["ebgp"]):
      apply_neighbor_attributes(ndata, ngb, intf, topology)

    _check_node_ibgp_local_role(ndata, topology)

    for intf, ngb in _bgp.intf_neighbors(ndata, select=["ibgp", "localas_ibgp"]):
      _check_ibgp_local_role(ndata, topology, intf)
