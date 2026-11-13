#
# Test plugin loaded by a device used in the lab topology (see device-plugin.yml)
#
from box import Box


def pre_transform(topology: Box) -> None:
  topology.message = f'{topology.name}: device plugin loaded'
