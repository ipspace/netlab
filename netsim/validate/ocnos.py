# Top-level OcNOS validation plugin
#
# OcNOS show output is CLI text (not JSON). Because OcNOS cmlsh rejects
# non-interactive SSH commands, the OSPF/BGP/IS-IS validators fetch it through the ansible
# validation action (netsim/cli/validate/ansible.py, via the ipinfusion.ocnos
# Ansible module); the per-module validators screen-scrape the CLI text.
# See netsim/validate/<module>/ocnos.py.
from netsim.validate.bgp.ocnos import *
from netsim.validate.isis.ocnos import *
from netsim.validate.ospf.ocnos import *
