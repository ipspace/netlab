# Top-level FRR validation plugin
#
# Import FRRouting OSPF and BGP checks and Linux ping/route checks
#
from box import Box
from netsim.validate.ospf.frr import *
from netsim.validate.isis.frr import *
from netsim.validate.bgp.frr import *
from netsim.validate.route.frr import *
from netsim.validate.linux import *
