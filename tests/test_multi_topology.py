#!/usr/bin/env python3

from netsim.utils import log
from netsim.utils import read as _read


def test_multi_topology_merge() -> None:
  log.init_log_system(header=False)
  topology = _read.load(
    [
      'topology/input/multi-topology-underlay.yml',
      'topology/input/multi-topology-overlay.yml',
    ],
    relative_topo_name=True,
    user_defaults=[],
  )
  log.exit_on_error()

  assert topology.input[:2] == [
    'topology/input/multi-topology-underlay.yml',
    'topology/input/multi-topology-overlay.yml',
  ]
  assert set(topology.nodes.keys()) == { 'r1', 'r2', 'r3' }
  assert topology.module == [ 'ospf' ]
  assert len(topology.links) == 2
  assert topology.message == "Underlay message.\nOverlay message.\n"
