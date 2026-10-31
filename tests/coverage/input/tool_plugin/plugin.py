#
# Test plugin loaded by an active external tool (see tools-plugin.yml)
#
from box import Box


def pre_transform(topology: Box) -> None:
  topology.tools.plugin_test.docker.up = f'echo "{topology.name} tool started by plugin"'
