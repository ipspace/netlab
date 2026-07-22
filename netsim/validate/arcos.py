# Top-level ArcOS validation plugin
#
# ArcOS is a native containerlab container (arrcus_arcos). On this build SSH/NETCONF/gNMI are
# disabled, so validation reads DUT state over the SAME docker-exec + confd_cli path used to deploy
# config (devices/arcos.yml -> clab.group_vars.netlab_show_command runs
#   printf 'show <path> | display json' | confd_cli -C -u admin  over ansible_connection: docker).
# Each module's checks parse the returned OpenConfig JSON.
from netsim.validate.bgp.arcos import *
from netsim.validate.isis.arcos import *
from netsim.validate.ospf.arcos import *
from netsim.validate.routing.arcos import *
