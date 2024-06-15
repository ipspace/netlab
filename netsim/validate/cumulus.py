"""
Top-level Cumulus Linux validation plugin

Import:

* FRRouting BGP checks
* Linux ping/route checks
"""

from box import Box
from netsim.validate.bgp.frr import *
from netsim.validate.linux import *
from netsim.validate.ospf.frr import show_ospf_neighbor,valid_ospf_neighbor,show_ospf_prefix,valid_ospf_prefix
