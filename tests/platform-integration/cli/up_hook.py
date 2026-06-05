#
# Plugin used to test "netlab up" hook
#

import pathlib

from box import Box

from netsim.data import append_to_list


def init(topology: Box) -> None:
  append_to_list(topology.defaults.netlab.up,'plugin','up_hook')

def pre_shell_pre_probe(topology: Box) -> None:
  with pathlib.Path("pre_probe.hook").open("w") as f:
    f.write('Hello, handsome ;)')
