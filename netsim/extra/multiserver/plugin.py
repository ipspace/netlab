"""
multiserver plugin — split a netlab topology across multiple workers.

Generates per-server containerlab topology files with cross-server VXLAN links.
See docs/plugins/multiserver.md for usage, examples, and configuration reference.
"""

import os
import pickle
import shutil
from pathlib import Path

import yaml
from box import Box

from netsim import __version__
from netsim.augment.config import make_paths_absolute
from netsim.augment.topology import cleanup_topology
from netsim.cli.external_commands import run_command
from netsim.data import append_to_list
from netsim.modules import _dataplane
from netsim.outputs import _TopologyOutput
from netsim.utils import files as _files
from netsim.utils import log, templates

_execute_after = ["fabric", "node.clone"]


# ---------------------------------------------------------------------------
#  Hook: init — validate config + register output hook
# ---------------------------------------------------------------------------


def init(topology: Box) -> None:
  ms = topology.get("multiserver", None)
  if not ms:
    return

  # Merge plugin defaults with user config (user values take priority)
  defaults = topology.defaults.get("multiserver", Box({}))
  topology.multiserver = defaults + ms
  ms = topology.multiserver
  servers = ms.get("servers", Box({}))

  if not servers:
    log.error('multiserver plugin requires a "servers" dictionary', log.MissingValue, "multiserver")
    return

  _validate_servers(servers)
  log.exit_on_error()

  # Register the output hook so netlab create calls our output() function
  append_to_list(topology.defaults.netlab.create, "plugin", "multiserver")
  append_to_list(topology.defaults.netlab.up, "plugin", "multiserver")
  append_to_list(topology.defaults.netlab.down, "plugin", "multiserver")


# ---------------------------------------------------------------------------
#  Hook: post_transform — resolve server assignments, classify links
# ---------------------------------------------------------------------------


def post_transform(topology: Box) -> None:
  ms = topology.get("multiserver", None)
  if not ms:
    return

  # topology.provider is guaranteed to be set by post_transform time
  if topology.provider != "clab":
    log.error(
      f'multiserver plugin currently supports only the "clab" provider, not "{topology.provider}"',
      log.IncorrectValue,
      "multiserver",
      more_hints=["libvirt and virtualbox support may be added in a future release"],
    )
    return

  server_map = {s.id: s for s in ms.servers.values()}
  replicated = _resolve_replicated(ms, topology)
  assignment = _resolve_assignments(ms.servers, topology)

  unassigned = {n for n in topology.nodes if n not in assignment and n not in replicated}
  if unassigned:
    if ms.get("assignment", "explicit") == "explicit":
      log.error(
        f"Nodes not assigned to any server: {', '.join(sorted(unassigned))}",
        log.MissingValue,
        "multiserver",
        more_hints=[
          "Assign nodes via multiserver.servers[].groups or .members",
          "Or set multiserver.assignment: auto for round-robin distribution",
        ],
      )
    else:
      _auto_distribute(unassigned, server_map, assignment, topology)

  log.exit_on_error()

  vni_base = ms.vxlan.get("vni_base", 10000)
  cross_count = _classify_links(topology, assignment, replicated, vni_base)
  log.exit_on_error()

  # Assigning a plain dict auto-converts to Box (default_box=True, box_dots=True)
  topology._multiserver = {
    "assignment": assignment,
    "server_map": server_map,
    "replicated": sorted(replicated),
  }

  _log_assignment_summary(ms, assignment, replicated, topology, vni_base, cross_count)


# ---------------------------------------------------------------------------
#  Hook: output — generate per-server clab.yml + VXLAN scripts
# ---------------------------------------------------------------------------


def output(topology: Box) -> None:
  ms = topology.get("multiserver", None)
  ms_data = topology.get("_multiserver", None)
  if not ms or not ms_data:
    return

  assignment = ms_data.assignment
  server_map = ms_data.server_map
  vxlan_cfg = ms.vxlan
  out_tpl = ms.get("output_dir", "server-{server_name}")

  replicated = set(ms_data.get("replicated", []))
  server_folders = []

  for sname, server in ms.servers.items():
    sid = server.id
    local_nodes = {n for n, s in assignment.items() if s == sid} | replicated
    if not local_nodes:
      continue

    out_dir = out_tpl.format(name=topology.name, server_name=sname, server_id=sid)
    server_folders.append((out_dir, local_nodes))

    if Path(out_dir).exists():
      shutil.rmtree(out_dir)
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    topo_copy, vxlan_tunnels = _build_server_topo(topology, local_nodes, sid, server_map, vxlan_cfg)

    # Write clab.yml via the standard clab.j2 template
    search_path = _files.get_search_path("clab", pkg_path_component="templates/provider/clab")
    clab_text = templates.render_template(
      data=topo_copy.to_dict(),
      j2_file="clab.j2",
      extra_path=search_path,
    )
    (Path(out_dir) / "clab.yml").write_text(clab_text)

    # Generate VXLAN setup/teardown scripts for multi-access bridge tunnels.
    # Register CLI hooks inside this server's snapshot so 'netlab up --snapshot'
    # (run from inside server-<name>/ on the worker) executes them automatically.
    # The hooks must live in topo_copy — they fire on the worker, not the
    # controller, which only runs 'netlab create'.
    if vxlan_tunnels:
      dev = server.get("vxlan_dev", "") or vxlan_cfg.get("dev", "")
      if not dev:
        log.error(
          f'Server "{sname}" has multi-access cross-server links but no VXLAN device is configured',
          log.MissingValue,
          "multiserver",
          more_hints=["Set multiserver.vxlan.dev or multiserver.servers[].vxlan_dev"],
        )
        continue
      _write_vxlan_scripts(out_dir, vxlan_tunnels, dev)
    # Write filtered snapshot so 'netlab up --snapshot' works per-server.
    _write_server_snapshot(topo_copy, out_dir)

    link_count = len(topo_copy.get("links", []))
    vx_count = len(vxlan_tunnels)
    parts = [f"{len(local_nodes)} nodes", f"{link_count} links"]
    if vx_count:
      parts.append(f"{vx_count} VXLAN tunnels")
    log.info(f'Server "{sname}": {out_dir}/ — {", ".join(parts)}', module="multiserver")

  # Stash the folder list for post_output(), which copies node_files/host_vars/
  # hosts.yml into each server folder after netlab has written them.
  if server_folders:
    topology._multiserver.server_folders = [[out_dir, sorted(nodes)] for out_dir, nodes in server_folders]

  # Flag the controller so the pre_probe hook aborts 'netlab up' instead of
  # starting the unsplit topology locally. Set after the loop, so server snapshots
  # don't capture it; workers run --snapshot and never reach output().
  topology.defaults.multiserver._control_node_abort = [out_dir for out_dir, _ in server_folders]


# ---------------------------------------------------------------------------
#  Hook: post_output — distribute generated files into per-server folders
# ---------------------------------------------------------------------------


def post_output(topology: Box) -> None:
  """Copy netlab-generated files into each server folder.

  Runs after 'netlab create' has written node_files/, host_vars/, hosts.yml, etc.
  netlab fires this hook for us, so there is no need for an atexit handler.
  """
  ms = topology.get("multiserver", None)
  ms_data = topology.get("_multiserver", None)
  if not ms or not ms_data:
    return

  server_folders = [(out_dir, set(nodes)) for out_dir, nodes in ms_data.get("server_folders", [])]
  if not server_folders:
    return

  copy_dirs = list(ms.get("copy_dirs", [])) + list(ms.get("extra_copy_dirs", []))
  copy_files = list(ms.get("copy_files", [])) + list(ms.get("extra_copy_files", []))
  _distribute_files(os.getcwd(), server_folders, copy_dirs, copy_files)


def _distribute_files(lab_folder: str, server_folders: list, copy_dirs: list, copy_files: list) -> None:
  """Distribute generated files into per-server directories."""
  lab_path = Path(lab_folder)
  nf_dir = lab_path / "node_files"
  hv_dir = lab_path / "host_vars"

  for sf, local_nodes in server_folders:
    sf_path = Path(sf)
    if not sf_path.is_dir():
      continue

    # node_files: per-node dirs + shared entries (names starting with -)
    # Always replace to avoid stale files from a previous run.
    if nf_dir.is_dir():
      dst_nf = sf_path / "node_files"
      if dst_nf.exists():
        shutil.rmtree(dst_nf)
      dst_nf.mkdir()
      for item in nf_dir.iterdir():
        if item.name in local_nodes or item.name.startswith("-"):
          _copy(item, dst_nf / item.name)

    # host_vars: per-node only
    if hv_dir.is_dir():
      dst_hv = sf_path / "host_vars"
      if dst_hv.exists():
        shutil.rmtree(dst_hv)
      dst_hv.mkdir()
      for item in hv_dir.iterdir():
        if item.name in local_nodes:
          _copy(item, dst_hv / item.name)

    # Configurable subdirectories (group_vars, templates, …)
    for dname in copy_dirs:
      src = lab_path / dname
      if src.is_dir():
        dst = sf_path / dname
        if dst.exists():
          shutil.rmtree(dst)
        shutil.copytree(src, dst)

    # Configurable top-level files (ansible.cfg, …)
    for fname in copy_files:
      src = lab_path / fname
      if src.exists():
        shutil.copy2(src, sf_path / fname)

    # Ansible inventory: copy hosts.yml filtered to local nodes only
    _write_filtered_inventory(lab_path / "hosts.yml", sf_path / "hosts.yml", local_nodes)


def _write_filtered_inventory(src: Path, dst: Path, local_nodes: set) -> None:
  """Write a hosts.yml containing only the nodes assigned to this server.

  A filtered inventory prevents 'netlab initial' on the worker from
  attempting to configure nodes that live on other servers.
  """
  if not src.exists():
    return
  try:
    with open(src) as f:
      inv = yaml.safe_load(f)
    if not isinstance(inv, dict):
      shutil.copy2(src, dst)
      return

    # Prune every 'hosts' dict to only local nodes
    def _prune(group: dict) -> None:
      if "hosts" in group and isinstance(group["hosts"], dict):
        group["hosts"] = {k: v for k, v in group["hosts"].items() if k in local_nodes}
      for child in group.get("children", {}).values():
        if isinstance(child, dict):
          _prune(child)

    for grp in inv.values():
      if isinstance(grp, dict):
        _prune(grp)

    with open(dst, "w") as f:
      yaml.dump(inv, f, default_flow_style=False)
  except Exception as e:
    # Falling back to the unfiltered inventory means 'netlab initial' on the
    # worker may try to configure nodes that live on other servers, so
    # make the failure visible instead of silently degrading.
    log.error(
      f"Could not filter Ansible inventory {src} -> {dst}: {e}",
      log.IncorrectValue,
      "multiserver",
      more_hints=["Copied the unfiltered hosts.yml instead; it may list nodes on other servers"],
    )
    shutil.copy2(src, dst)


def _copy(src: Path, dst: Path) -> None:
  try:
    if src.is_dir():
      shutil.copytree(src, dst)
    else:
      shutil.copy2(src, dst)
  except Exception as e:
    # node_files/host_vars carry the per-node configs; a silent failure here
    # leaves an incomplete server directory, so surface it instead of swallowing.
    log.error(
      f"Could not copy {src} -> {dst}: {e}",
      log.IncorrectValue,
      "multiserver",
    )


# ===========================================================================
#  Internal helpers — post_transform
# ===========================================================================


def _validate_servers(servers: Box) -> None:
  # servers is a dict keyed by server name, so duplicate names are impossible by construction.
  # Mixed static/auto ID assignment uses the same _dataplane pattern as VLANs/VRFs.
  _dataplane.create_id_set("multiserver_server")
  _dataplane.extend_id_set(
    "multiserver_server", _dataplane.build_id_set(Box({"servers": servers}), "servers", "id", "multiserver")
  )
  _dataplane.set_id_counter("multiserver_server", 1, max_value=65535)

  for name, s in servers.items():
    if "id" not in s:
      s.id = _dataplane.get_next_id("multiserver_server")


def _resolve_replicated(ms: Box, topology: Box) -> set:
  # Each entry's validity (node or group name) is checked by the schema
  # (node_or_group subtype on multiserver.replicate). Here we only expand
  # group references into their members. Called from post_transform where
  # group members are already resolved.
  replicated: set = set()
  for entry in ms.get("replicate", []):
    if entry in topology.nodes:
      replicated.add(entry)
    else:
      for member in topology.groups[entry].get("members", []):
        replicated.add(member)
  return replicated


def _resolve_assignments(servers: Box, topology: Box) -> dict:
  # Group and node name existence is validated by the schema (group_id/node_id
  # subtypes on multiserver.servers[].groups/.members), so we only need to expand
  # references and catch double-assignment conflicts here.
  assignment: dict = {}

  def _assign(member: str, server: Box, sname: str) -> None:
    if member in assignment and assignment[member] != server.id:
      log.error(
        f'Node {member} assigned to both server {assignment[member]} and "{sname}"',
        log.IncorrectValue,
        "multiserver",
      )
    assignment[member] = server.id

  for sname, server in servers.items():
    for gname in server.get("groups", []):
      for member in topology.groups[gname].get("members", []):
        _assign(member, server, sname)
    for member in server.get("members", []):
      _assign(member, server, sname)

  return assignment


def _auto_distribute(unassigned: set, server_map: dict, assignment: dict, topology: Box) -> None:
  """Distribute unassigned nodes across servers, keeping netlab groups together.

  Load is measured as (assigned node count) / weight, where weight defaults to 1.
  A server with weight=2 absorbs twice as many nodes before being considered
  "as loaded" as a server with weight=1.
  """
  sorted_sids = sorted(server_map.keys())
  weights = {sid: max(1, int(server_map[sid].get("weight", 1))) for sid in sorted_sids}
  counts = {sid: sum(1 for s in assignment.values() if s == sid) for sid in sorted_sids}

  def _load(sid: int) -> float:
    return counts[sid] / weights[sid]

  # Build group buckets: keep group members together, distribute largest groups first
  claimed: set = set()
  group_buckets: list = []
  for gdata in topology.get("groups", {}).values():
    members = [m for m in gdata.get("members", []) if m in unassigned and m not in claimed]
    if members:
      group_buckets.append(members)
      claimed.update(members)
  group_buckets.sort(key=lambda g: -len(g))

  for members in group_buckets:
    target = min(sorted_sids, key=_load)
    for m in members:
      assignment[m] = target
    counts[target] += len(members)

  # Remaining ungrouped nodes: one by one to least-loaded server
  for name in sorted(unassigned - claimed):
    target = min(sorted_sids, key=_load)
    assignment[name] = target
    counts[target] += 1


def _classify_links(topology: Box, assignment: dict, replicated: set, vni_base: int) -> int:
  """Assign _ms metadata to each link; return the number of cross-server links."""
  vni = vni_base
  for link in topology.links:
    link_servers = {
      assignment[i.node] for i in link.get("interfaces", []) if i.node not in replicated and i.node in assignment
    }
    # A link with a physical uplink (clab.uplink) attaches to the external lab
    # network on EVERY server via that server's own NIC, so the physical fabric
    # already provides cross-server connectivity. Tunneling it would add a
    # redundant path and an L2 loop (uplink + VXLAN on the same bridge, no STP)
    # → broadcast storm. Never VXLAN uplink bridges; just keep them local.
    has_uplink = bool(link.get("clab", {}).get("uplink"))
    if len(link_servers) > 1 and not has_uplink:
      link._ms = Box({"cross": True, "vni": vni, "servers": sorted(link_servers)})
      vni += 1
    else:
      link._ms = Box({"cross": False, "servers": sorted(link_servers)})

  if vni > 16777215:
    log.error(f"VXLAN VNI overflow: {vni} exceeds 24-bit maximum (16777215)", log.IncorrectValue, "multiserver")

  return vni - vni_base


def _log_assignment_summary(
  ms: Box, assignment: dict, replicated: set, topology: Box, vni_base: int, cross_count: int
) -> None:
  for sname, server in ms.servers.items():
    sid = server.id
    server_nodes = sorted(n for n, s in assignment.items() if s == sid)
    n = len(server_nodes)

    server_groups = []
    for gname, gdata in topology.get("groups", {}).items():
      members = gdata.get("members", [])
      if not members:
        continue
      on_this = [m for m in members if assignment.get(m) == sid]
      assigned = [m for m in members if m in assignment]
      if on_this and len(on_this) == len(assigned):
        server_groups.append(gname)

    log.info(f'Server "{sname}" ({server.host}): {n} nodes', module="multiserver")
    if server_groups:
      preview = server_groups[:8]
      suffix = f" ... +{len(server_groups) - 8} more" if len(server_groups) > 8 else ""
      log.info(f"  groups: {', '.join(preview)}{suffix}", module="multiserver")
    if n <= 20:
      log.info(f"  nodes:  {', '.join(server_nodes)}", module="multiserver")
    else:
      log.info(f"  nodes:  {', '.join(server_nodes[:6])} ... +{n - 6} more", module="multiserver")

  if replicated:
    log.info(f"Replicated on all servers: {', '.join(sorted(replicated))}", module="multiserver")
  if cross_count:
    log.info(f"{cross_count} cross-server links (VNI {vni_base}–{vni_base + cross_count - 1})", module="multiserver")


# ===========================================================================
#  Internal helpers — per-server topology filtering
# ===========================================================================


def _build_server_topo(topology: Box, local_nodes: set, sid: int, server_map: dict, vxlan_cfg: Box) -> tuple:
  """Return (topo_copy, vxlan_tunnels) for one server.

  topo_copy is a filtered Box ready to pass to clab.j2:
  - Only local nodes are kept.
  - Each link that has at least one local interface is kept; remote interfaces
    are pruned so node_count reflects only what this server sees.
  - Cross-server P2P links get link.clab.vxlan annotated so clab.j2 renders
    a native VXLAN endpoint instead of a regular veth pair.
  - Cross-server bridge links keep their bridge but also produce host-level
    VXLAN tunnel entries returned in vxlan_tunnels.
  """
  dstport = vxlan_cfg.get("dstport", 4789)
  assignment = topology._multiserver.assignment

  topo_copy = Box(topology, box_dots=True, default_box=True)
  topo_copy.nodes = Box({n: v for n, v in topology.nodes.items() if n in local_nodes}, box_dots=True)

  vxlan_tunnels: list = []
  filtered_links = []

  for link in topology.links:
    local_intfs = [i for i in link.get("interfaces", []) if i.node in local_nodes]
    if not local_intfs:
      continue

    lc = Box(link, box_dots=True, default_box=True)
    is_cross = link.get("_ms.cross", False)

    if not is_cross:
      # Local link: prune interfaces to just local ones and update node_count.
      lc.interfaces = local_intfs
      lc.node_count = len(local_intfs)
      filtered_links.append(lc)
      continue

    vni = link._ms.vni
    node_count = link.get("node_count", len(link.get("interfaces", [])))

    if node_count == 2:
      # Cross-server P2P: keep only the local interface, annotate clab.vxlan.
      # clab.j2 sees node_count==2 and l.clab.vxlan defined → renders VXLAN endpoint.
      remote_sid = next(
        (assignment[i.node] for i in link.get("interfaces", []) if assignment.get(i.node) not in (None, sid)),
        None,
      )
      if remote_sid is None:
        continue
      lc.interfaces = local_intfs
      lc.node_count = 2
      lc.clab.vxlan = Box(
        {
          "vni": vni,
          "remote": str(server_map[remote_sid].host),
          "dstport": dstport,
        }
      )
      filtered_links.append(lc)
    else:
      # Cross-server bridge: prune to local interfaces, let clab.j2 render the bridge.
      lc.interfaces = local_intfs
      lc.node_count = len(local_intfs)
      filtered_links.append(lc)

      # Host-level VXLAN tunnels for the bridge (expressed as shell scripts).
      bridge = link.get("bridge", f"br{link.linkindex}")
      remote_sids = {
        assignment[i.node] for i in link.get("interfaces", []) if assignment.get(i.node) not in (None, sid)
      }
      for rsid in sorted(remote_sids):
        vxlan_tunnels.append(
          {
            "bridge": bridge,
            "vni": vni,
            "remote": str(server_map[rsid].host),
            "dstport": dstport,
            "remote_id": rsid,
          }
        )

  topo_copy.links = filtered_links
  return topo_copy, vxlan_tunnels


# ---------------------------------------------------------------------------
#  File operations
# ---------------------------------------------------------------------------


def _write_server_snapshot(topo_copy: Box, out_dir: str) -> None:
  """Write a filtered netlab snapshot for this server's nodes only."""
  snap = Box(topo_copy, box_dots=True)

  # Remove prefix generators and serialize
  cleaned = cleanup_topology(snap)
  topodict = cleaned.to_dict()
  topodict["_netlab_version"] = __version__

  with open(Path(out_dir) / "netlab.snapshot.pickle", "wb") as f:
    pickle.dump(topodict, f)


def pre_shell_pre_probe(topology: Box) -> None:
  """pre_probe hook fired by 'netlab up' before it probes providers.

  On the controller the flag is set (output() ran during create), so we abort
  before starting the unsplit topology. On a worker it's absent, and we
  resolve search paths and refresh the snapshot/inventory as before.
  """
  abort = topology.defaults.get("multiserver", {}).get("_control_node_abort", None)
  if abort:
    folders = "\n".join(f"  - {f}/" for f in abort)
    log.fatal(
      "multiserver: per-server configurations have been generated; "
      "'netlab up' will not start the merged topology on the controller.\n"
      f"Generated server folders:\n{folders}\n"
      "Copy each folder to its worker and run 'netlab up --snapshot' there "
      "(see docs/plugins/multiserver.md, Deployment Workflow).",
      "multiserver",
    )

  if "paths" in topology.get("defaults", {}):
    make_paths_absolute(topology.defaults.paths)

  # Re-write the updated snapshot to the current directory (which is where we started)
  _write_server_snapshot(topology, ".")

  # Re-create the Ansible inventory to populate group_vars with the local paths
  ansible_settings = topology.defaults.outputs.get("ansible", Box({}))
  output_module = _TopologyOutput.load("ansible", ansible_settings)
  if output_module:
    output_module.write(topology)


def pre_shell_post_start_lab(topology: Box) -> None:
  """Post start lab hook: run VXLAN setup script if auto_start is enabled."""
  ms = topology.get("multiserver", None)
  if ms and not ms.vxlan.get("auto_start", True):
    return

  if os.path.exists("vxlan-setup.sh"):
    run_command("bash vxlan-setup.sh")


def pre_shell_pre_stop_lab(topology: Box) -> None:
  """Pre stop lab hook: run VXLAN teardown script if auto_start is enabled."""
  ms = topology.get("multiserver", None)
  if ms and not ms.vxlan.get("auto_start", True):
    return

  if os.path.exists("vxlan-teardown.sh"):
    run_command("bash vxlan-teardown.sh")


def _write_vxlan_scripts(out_dir: str, tunnels: list, dev: str) -> None:
  """Generate bash scripts to create/destroy host-level VXLAN tunnels."""
  # Deduplicate tunnels: same VNI+remote pair should only appear once
  seen: set = set()
  unique_tunnels = []
  for t in tunnels:
    key = (t["vni"], t["remote"])
    if key not in seen:
      seen.add(key)
      unique_tunnels.append(t)

  tpl_dir = str(Path(__file__).parent)
  tpl_data = {"tunnels": unique_tunnels, "dev": dev}

  for script, tpl in [("vxlan-setup.sh", "vxlan-setup.j2"), ("vxlan-teardown.sh", "vxlan-teardown.j2")]:
    text = templates.render_template(data=tpl_data, j2_file=tpl, path=tpl_dir)
    path = Path(out_dir) / script
    path.write_text(text)
    os.chmod(path, 0o755)
