#
# cRPD is running on top of Linux and starts a Linux shell, making it
# possible to do Linux pings in validation checks
#
# However, we have to tell Ruff that we know what we're doing ;)
#
from netsim.validate.linux import exec_ping, valid_ping  # noqa: F401
