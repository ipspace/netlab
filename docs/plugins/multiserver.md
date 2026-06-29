(plugin-multiserver)=
# Splitting Topologies Across Multiple Workers

The *multiserver* plugin distributes a single *netlab* topology across multiple workers. The controller is the system where you run `netlab create`; each worker can be a bare-metal server or a VM and runs one generated containerlab topology. The plugin assigns nodes to worker entries, classifies links as local or cross-worker, and generates a self-contained containerlab configuration directory for each worker with VXLAN-based interconnects.

```eval_rst
.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none
```

```{warning}
* All workers must have direct IP reachability (e.g. over a management network or dedicated interconnect).
```

## Using the Plugin

* Add `plugin: [ multiserver ]` to lab topology.
* Define target workers in the **multiserver.servers** dictionary.
* Choose an assignment mode (`explicit` or `auto`) with **multiserver.assignment**.

The plugin runs during `netlab create` on the controller and generates self-contained per-worker directories (e.g. `server-srv1/`, `server-srv2/`) with tailored `clab.yml` files, node configs, and VXLAN scripts ready for deployment on the workers.

## Configuring Plugin Parameters

The plugin is configured with the **multiserver** topology-level dictionary that has these parameters:

| Parameter | Type | Meaning |
|-----------|------|---------|
| **assignment** | string | How to assign nodes to workers: `explicit` (default) or `auto` |
| **servers** | dictionary | Target workers, keyed by worker name |
| **vxlan** | dictionary | Global settings for VXLAN tunnels |
| **replicate** | list | Advanced: nodes or groups intentionally duplicated on all workers; see [Replicated Nodes](multiserver-replicate) before using |
| **output_dir** | string | Template for per-worker directory names (default: `server-{server_name}`); supports `{server_name}`, `{server_id}`, and `{name}` (topology name) |
| **copy_dirs** | list | Subdirectories copied into every worker directory (default: `[group_vars, templates]`); overrides the default list |
| **copy_files** | list | Top-level files copied into every worker directory (default: `[ansible.cfg]`); overrides the default list |
| **extra_copy_dirs** | list | Additional subdirectories to copy on top of **copy_dirs** |
| **extra_copy_files** | list | Additional top-level files to copy on top of **copy_files** |

(multiserver-servers)=
### Worker Parameters

The **multiserver.servers** dictionary is keyed by worker name (e.g. `srv1`, `dc-east`). Each entry represents one worker. The name is used for per-worker directory names and log messages, and because workers are a dictionary, duplicate worker names are impossible. Each entry supports these parameters:

| Parameter | Type | Meaning |
|-----------|------|---------|
| **id** | integer | Numeric identifier used for VXLAN bookkeeping; auto-assigned if omitted |
| **host** | string | IP address or hostname of the worker |
| **groups** | list | *netlab* groups whose members are assigned to this worker |
| **members** | list | Individual node names assigned to this worker |
| **vxlan_dev** | string | Worker interface to bind VXLAN tunnels to this worker |
| **weight** | integer | Relative capacity for auto-assignment (default: `1`); a worker with `weight: 2` absorbs twice as many nodes before being considered as loaded as a worker with `weight: 1` |

(multiserver-vxlan)=
### VXLAN Parameters

Global VXLAN settings are specified in the **multiserver.vxlan** dictionary:

| Parameter | Type | Meaning |
|-----------|------|---------|
| **vni_base** | integer | Starting VNI for cross-worker links (default: `10000`) |
| **dstport** | integer | UDP destination port for VXLAN traffic (default: `4789`) |
| **dev** | string | **Required.** Default worker interface to bind VXLAN tunnels |

VXLAN tunnels bind to the global interface specified in **multiserver.vxlan.dev**. If your workers use different interface names, you can override this interface per-worker using the **vxlan_dev** parameter under each worker in the **multiserver.servers** dictionary.

(multiserver-assignment)=
## Assignment Modes

### Explicit Assignment (Default)

In `explicit` mode, every node must be mapped to a worker using the **groups** or **members** attributes of a [worker entry](multiserver-servers). Any unassigned node (excluding [replicated nodes](multiserver-replicate)) results in an error.

```yaml
plugin: [ multiserver ]

multiserver:
  assignment: explicit
  servers:
    srv1:
      host: 192.168.168.128
      groups: [ core ]
      members: [ edge-node ]
    srv2:
      host: 192.168.168.129
      groups: [ spines, leaves ]
```

### Automatic Assignment

In `auto` mode, nodes that are not explicitly pinned to a worker are distributed automatically using a greedy balancing algorithm:

1. Nodes belonging to a *netlab* group are kept together — the entire group is placed on the worker with the lowest current load. Larger groups are placed first for better balance.
2. Remaining ungrouped nodes are assigned one at a time to the least-loaded worker.

**Load** is defined as `(assigned node count) / weight`, where **weight** defaults to `1`. Nodes already pinned via **groups** or **members** attributes count toward worker load, so the algorithm balances around any explicit assignments.

```yaml
plugin: [ multiserver ]

multiserver:
  assignment: auto
  servers:
    srv1:
      host: 192.168.168.128
    srv2:
      host: 192.168.168.129
```

Use **weight** to account for workers with different capacities. A worker with `weight: 2` is treated as twice as capable and absorbs proportionally more nodes before being considered equally loaded:

```yaml
multiserver:
  assignment: auto
  servers:
    srv1:
      host: 192.168.168.128
      weight: 1          # smaller worker
    srv2:
      host: 192.168.168.129
      weight: 2          # larger worker — gets roughly twice as many nodes
```

```{tip}
You can pin specific nodes or groups to a worker in `auto` mode using **groups** and **members** attributes. Only unassigned nodes are auto-distributed.
```

#### Group Granularity

Because auto mode keeps entire groups together on a single worker, the granularity of your groups directly affects how evenly nodes are distributed. Define groups at the smallest unit you want to keep on one worker.

For example, consider a topology with two sites, each containing five nodes:

```yaml
# BAD: one large group — all 10 nodes land on one worker
groups:
  sites:
    members: [ site1-r1, site1-r2, site1-r3, site1-r4, site1-r5,
               site2-r1, site2-r2, site2-r3, site2-r4, site2-r5 ]
```

```yaml
# GOOD: per-site groups — one site per worker
groups:
  site1:
    members: [ site1-r1, site1-r2, site1-r3, site1-r4, site1-r5 ]
  site2:
    members: [ site2-r1, site2-r2, site2-r3, site2-r4, site2-r5 ]
  sites:
    members: [ site1-r1, site1-r2, site1-r3, site1-r4, site1-r5,
               site2-r1, site2-r2, site2-r3, site2-r4, site2-r5 ]
```

```{tip}
You can also reference child groups by name in `members`, which is more concise and avoids repeating individual node names:

    sites:
      members: [ site1, site2 ]
```

In the second example the parent `sites` group can still be used for Ansible targeting or shared configuration — it does not affect placement because the child groups (`site1`, `site2`) claim their members first during assignment.

```{note}
Groups are processed in definition order. Child groups defined **before** a parent group will claim their members first, making the parent group a no-op for assignment. Always define fine-grained groups before aggregate groups in your topology.
```

## Complete Example

A minimal two-worker topology with explicit assignment:

```yaml
plugin: [ multiserver ]

provider: clab

groups:
  spines:
    members: [ s1, s2 ]
  leaves:
    members: [ l1, l2 ]

nodes:
  s1:
    device: srlinux
  s2:
    device: srlinux
  l1:
    device: srlinux
  l2:
    device: srlinux

links:
  - s1-l1
  - s1-l2
  - s2-l1
  - s2-l2

multiserver:
  assignment: explicit
  servers:
    spine-host:
      host: 192.168.168.128
      groups: [ spines ]
      vxlan_dev: eth0           # Override per-worker (optional)
    leaf-host:
      host: 192.168.168.129
      groups: [ leaves ]
      vxlan_dev: eth1           # Override per-worker (optional)
  vxlan:
    vni_base: 10000
    dev: eth0                   # Required: global default interface
```

This places spines on `spine-host` and leaves on `leaf-host`. All four links cross workers and are provisioned as containerlab native VXLAN endpoints.

## Behind the Scenes

When the plugin processes the topology, it classifies links into three categories:

* **Local links** connecting nodes on the same worker remain as regular containerlab veth pairs or bridges.
* **Cross-worker point-to-point links** are provisioned via containerlab's native VXLAN link endpoints (`type: vxlan` in `clab.yml`).
* **Cross-worker multi-access links** use a local Linux bridge on each worker, interconnected via worker VXLAN tunnels configured by generated setup scripts.

Each per-worker directory is self-contained and includes:

* A tailored `clab.yml` with only the relevant nodes and cross-worker VXLAN interfaces
* A filtered `netlab.snapshot.pickle` for use with `netlab up --snapshot`
* A filtered `hosts.yml` containing only the nodes assigned to that worker, so `netlab initial` does not attempt to configure nodes on other workers
* Copies of `node_files/` and `host_vars/` for only the nodes on that worker
* Copies of the directories and files listed in **multiserver.copy_dirs** and **multiserver.copy_files**
* Per-worker `vxlan-setup.sh` and `vxlan-teardown.sh` scripts (when multi-access VXLAN tunnels are needed), registered in that worker's snapshot as [CLI hooks](dev-cli-hooks) (`netlab.up.post_start_clab` / `netlab.down.pre_stop_clab`) so `netlab up` and `netlab down` run them automatically on the worker

(multiserver-deployment)=
## Deployment Workflow

```{note}
The plugin does **not** orchestrate workers. It runs only on the controller during `netlab create`, where it generates a self-contained directory per worker. It never opens SSH connections, runs commands remotely, or copies files to other systems. You copy each directory to its worker yourself (Step 2), and `netlab` then runs **independently on each worker** (Step 3) — the per-worker VXLAN CLI hooks fire locally on that worker, not from the controller.
```

**Step 1: Generate configurations** on the controller:

```bash
netlab create topology.yml
```

The plugin automatically copies all required files into each worker directory — no extra bundling step is needed.

**Step 2: Copy worker directories to workers** (e.g. via rsync):

```bash
rsync -avz server-spine-host/ user@192.168.168.128:~/lab/server-spine-host/
rsync -avz server-leaf-host/ user@192.168.168.129:~/lab/server-leaf-host/
```

**Step 3: Deploy on each worker** by running the following command there:

```bash
netlab up --snapshot -vv
```

When multi-access VXLAN tunnels are present, `netlab up` runs `vxlan-setup.sh` automatically via a [CLI hook](dev-cli-hooks) registered by the plugin.

```{important}
**Why is `--snapshot` required on workers?**

You must run `netlab up --snapshot` on workers to load the topology from the pre-generated snapshot (`netlab.snapshot.pickle`) instead of the original `topology.yml`.

Running with `topology.yml` directly on workers will fail because:
1. **Consistency**: Netlab dynamically allocates IP addresses, interface IDs, and VXLAN VNIs. Independent creation runs on different workers would result in mismatched allocations.
2. **Recursion**: Running `netlab create` on `topology.yml` on the workers would execute the `multiserver` plugin again, causing it to split the topology recursively and generate nested server subdirectories.
```

**Teardown** on each worker:

```bash
netlab down
```

When multi-access VXLAN tunnels are present, `netlab down` runs `vxlan-teardown.sh` automatically via a CLI hook registered by the plugin.

## Customising What Gets Copied

By default, the plugin copies `group_vars/` and `templates/` subdirectories, plus `ansible.cfg`, into every worker directory. To add extra items on top of the defaults, use **extra_copy_dirs** and **extra_copy_files**:

```yaml
multiserver:
  extra_copy_dirs: [ monitoring ]
  extra_copy_files: [ netlab.lock ]
```

To replace the defaults entirely, use **copy_dirs** and **copy_files**:

```yaml
multiserver:
  copy_dirs: [ group_vars, templates, monitoring ]
  copy_files: [ ansible.cfg, netlab.lock ]
```

The Ansible inventory (`hosts.yml`) is always written into each worker directory and is automatically filtered to contain only the nodes assigned to that worker.

## Limitations

* Only the **containerlab** provider is supported. Libvirt and virtualbox topologies cannot be split across workers.
* Cross-worker VXLAN tunnels use a flat VNI space starting at **vni_base**. The maximum VNI value is 16777215 (24-bit). Topologies with more than ~16 million cross-worker links will fail validation, if you somehow manage to hit that number ;)
* All workers must have direct IP reachability — the plugin does not support NAT traversal or relay hosts between workers.

(multiserver-replicate)=
## Replicated Nodes

```{warning}
Replicated nodes are an advanced feature intended for out-of-band, per-worker services. The plugin does not create a cluster, synchronize state between replicas, prevent split-brain scenarios, or assign unique per-replica addresses.
```

Nodes or groups listed in **multiserver.replicate** are instantiated in every per-worker topology. The node definition, generated configuration, and allocated addresses are copied unchanged into every worker directory.

Links connecting to replicated nodes are always treated as local, so traffic between a replicated node and its neighbors never crosses the VXLAN overlay.

A typical safe use case is a local monitoring or telemetry stack. For example, every worker could run its own exporter, collector, or dashboard container that reads Docker/containerlab state from the local host or scrapes only the lab nodes placed on that worker. Those services are outside the simulated network's routing and forwarding behavior; they observe the lab but do not become part of it.

Do not attach replicated nodes to a shared external or management segment unless you provide unique addressing outside the multiserver plugin. Otherwise, the duplicate IP or MAC addresses become visible in the same L2/L3 domain.

```yaml
multiserver:
  assignment: auto
  servers:
    srv1:
      host: 192.168.168.128
    srv2:
      host: 192.168.168.129
  replicate: [ prometheus, grafana ]
```
