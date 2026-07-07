#
# VPP quirks
#
from box import Box

from ..augment import devices as a_devices
from ..utils import log
from . import _Quirks
from .bird import bird_vlan_evpn_rt, bird_vrf_rt

_VALID_CP = ("bird", "frr")


def control_plane(node: Box, defaults: Box) -> str:
  vpp_defaults = defaults.devices.vpp
  return node.get("control_plane", vpp_defaults.get("control_plane", "bird"))


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
  cp_dev = topology.defaults.devices.get(cp, {})
  cp_clab_gvars = cp_dev.get("clab", {}).get("group_vars")
  cp_gvars = cp_dev.get("group_vars", {})
  vpp_clab_gvars = node.clab.get("group_vars", {})

  if cp_clab_gvars:
    node.clab.group_vars = cp_clab_gvars + vpp_clab_gvars

  for gvars in (cp_clab_gvars, cp_gvars):
    if not gvars:
      continue
    for k, v in gvars.items():
      if k not in node and k not in vpp_clab_gvars:
        node[k] = v


def _merge_cp_config_templates(node: Box, topology: Box, cp: str) -> None:
  cp_templates = topology.defaults.devices.get(cp, {}).get("clab", {}).get("node", {}).get("config_templates")
  if cp_templates:
    node.clab.config_templates = cp_templates + node.clab.get("config_templates", {})


def _bird_rt_transforms(node: Box) -> None:
  bird_vrf_rt(node)
  bird_vlan_evpn_rt(node)


def _configure_bird_cp(node: Box, topology: Box) -> None:
  _merge_cp_daemon_config(node, topology, "bird")
  _bird_rt_transforms(node)
  _merge_cp_group_vars(node, topology, "bird")


def _register_frr_cp_scripts(node: Box, topology: Box) -> None:
  """
  Bind FRR control-plane module scripts for startup-time deployment.

  netlab initial must not docker-exec these before FRR starts in the dataplane netns.
  """
  features = a_devices.get_device_features(node, topology.defaults)
  mod_list: list[str] = ["normalize"] if features.initial.get("normalize", False) else []
  mod_list += ["initial"] + node.get("module", []) + node.get("config", [])
  cp_modules = _active_cp_modules(node, "frr") - {"frr", "routing", "initial"}
  if not cp_modules:
    return

  if not node.get("_daemon_config"):
    node._daemon_config = {}

  for idx, m in enumerate(mod_list, start=1):
    if m not in cp_modules:
      continue
    node._daemon_config[m.replace(".", "@")] = f"/etc/config/{idx:02d}-{m}.sh"


def _configure_frr_cp(node: Box, topology: Box) -> None:
  _merge_cp_group_vars(node, topology, "frr")
  _merge_cp_config_templates(node, topology, "frr")
  _register_frr_cp_scripts(node, topology)


def configure_control_plane(node: Box, topology: Box) -> None:
  cp = control_plane(node, topology.defaults)
  if cp not in _VALID_CP:
    log.error(
      f"control_plane on node {node.name} must be one of {','.join(_VALID_CP)}",
      category=log.IncorrectValue,
      module="vpp",
    )
    return

  node.control_plane = cp

  if cp == "bird":
    node._daemon_parent = "bird"
    _configure_bird_cp(node, topology)
  else:
    _configure_frr_cp(node, topology)


class VPP(_Quirks):
  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    configure_control_plane(node, topology)
