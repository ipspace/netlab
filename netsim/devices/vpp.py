#
# VPP quirks
#
from box import Box

from ..data import append_to_list, filemaps
from ..utils import log
from . import _Quirks
from .bird import bird_vlan_evpn_rt, bird_vrf_rt

_VALID_CP = ("bird", "frr")


def vpp_control_plane(node: Box, topology: Box) -> str:
  defaults = topology.defaults.devices.vpp
  return node.get("vpp_control_plane", defaults.get("vpp_control_plane", "bird"))


def _bird_rt_transforms(node: Box) -> None:
  bird_vrf_rt(node)
  bird_vlan_evpn_rt(node)


def _merge_cp_daemon_config(node: Box, topology: Box, cp: str) -> None:
  cp_dev = topology.defaults.devices.get(cp)
  if not cp_dev or "daemon_config" not in cp_dev:
    return

  dc = node.get("_daemon_config")
  if not dc:
    node._daemon_config = cp_dev.daemon_config
    return

  for k, v in cp_dev.daemon_config.items():
    dc[k] = v


def _add_cp_clab_templates(node: Box, topology: Box, cp: str) -> None:
  if "clab" not in node:
    return

  cp_dev = topology.defaults.devices.get(cp)
  if not cp_dev or "daemon_config" not in cp_dev:
    return

  existing_sources = {item.source for item in node.clab.get("config_templates", [])}
  existing_targets = {item.target for item in node.clab.get("config_templates", [])}
  bind_targets = {item.target for item in node.clab.get("binds", [])}
  path = f"nodes.{node.name}"

  for k, v in cp_dev.daemon_config.items():
    kn = k.replace("@", ".")
    if kn in existing_sources:
      continue
    item = filemaps.normalize_item(path=path, module="vpp", key=k, value=v)
    if not item or item["target"] in existing_targets:
      continue
    append_to_list(node.clab, "config_templates", item)
    existing_sources.add(kn)
    existing_targets.add(item["target"])
    append_to_list(node, "netlab_ansible_skip_module", kn)
    if item["target"] in bind_targets:
      continue
    append_to_list(
      node.clab,
      "binds",
      {
        "source": f"node_files/{node.name}/{item['source']}",
        "target": item["target"],
      },
    )
    bind_targets.add(item["target"])


def _configure_bird_cp(node: Box, topology: Box) -> None:
  _merge_cp_daemon_config(node, topology, "bird")
  _bird_rt_transforms(node)
  _add_cp_clab_templates(node, topology, "bird")
  if "clab" not in node:
    return
  node.clab.group_vars.netlab_show_command = ["birdcl", "show $@"]


def _configure_frr_cp(node: Box) -> None:
  if "clab" not in node:
    return
  g_vars = node.clab.group_vars
  g_vars.netlab_show_command = ["vtysh", "-c", "show $@"]
  g_vars.netlab_default_shebang = "#!/usr/bin/vtysh -f"
  g_vars.netlab_config_exec = ["sleep 1"]


def configure_control_plane(node: Box, topology: Box) -> None:
  if node.device != "vpp":
    return

  cp = vpp_control_plane(node, topology)
  if cp not in _VALID_CP:
    log.error(
      f"vpp_control_plane on node {node.name} must be one of {','.join(_VALID_CP)}",
      category=log.IncorrectValue,
      module="vpp",
    )
    return

  node.vpp_control_plane = cp
  if cp == "bird":
    _configure_bird_cp(node, topology)
  else:
    _configure_frr_cp(node)


class VPP(_Quirks):
  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    configure_control_plane(node, topology)
