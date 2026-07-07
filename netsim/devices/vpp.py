#
# VPP quirks
#
from box import Box

from ..utils import log
from . import _Quirks
from .bird import bird_vlan_evpn_rt, bird_vrf_rt

_VALID_CP = ("bird", "frr")


def vpp_control_plane(node: Box, defaults: Box) -> str:
  vpp_defaults = defaults.devices.vpp
  return node.get("vpp_control_plane", vpp_defaults.get("vpp_control_plane", "bird"))


def _daemon_module(key: str) -> str:
  return key.replace("@", ".").split(".")[0]


def _active_cp_modules(node: Box, cp: str) -> set[str]:
  active = {cp, "routing"}
  active.update(node.get("module", []))
  return active


def _merge_cp_daemon_config(node: Box, topology: Box, cp: str) -> None:
  cp_dev = topology.defaults.devices.get(cp)
  if not cp_dev or "daemon_config" not in cp_dev:
    return

  active = _active_cp_modules(node, cp)
  dc = node.get("_daemon_config")
  if not dc:
    node._daemon_config = {}

  for k, v in cp_dev.daemon_config.items():
    if _daemon_module(k) not in active:
      continue
    node._daemon_config[k] = v


def _merge_cp_group_vars(node: Box, topology: Box, cp: str) -> None:
  cp_gvars = topology.defaults.devices.get(cp, {}).get("clab", {}).get("group_vars")
  if cp_gvars:
    node.clab.group_vars = cp_gvars + node.clab.group_vars


def _bird_rt_transforms(node: Box) -> None:
  bird_vrf_rt(node)
  bird_vlan_evpn_rt(node)


def _configure_bird_cp(node: Box, topology: Box) -> None:
  _merge_cp_daemon_config(node, topology, "bird")
  _bird_rt_transforms(node)
  _merge_cp_group_vars(node, topology, "bird")


def _configure_frr_cp(node: Box, topology: Box) -> None:
  _merge_cp_group_vars(node, topology, "frr")


def configure_control_plane(node: Box, topology: Box) -> None:
  if node.device != "vpp":
    return

  cp = vpp_control_plane(node, topology.defaults)
  if cp not in _VALID_CP:
    log.error(
      f"vpp_control_plane on node {node.name} must be one of {','.join(_VALID_CP)}",
      category=log.IncorrectValue,
      module="vpp",
    )
    return

  node.vpp_control_plane = cp

  if cp == "bird":
    node._daemon_parent = "bird"
    _configure_bird_cp(node, topology)
  else:
    _configure_frr_cp(node, topology)


class VPP(_Quirks):
  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    configure_control_plane(node, topology)
