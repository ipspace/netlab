# 'netsim clab' actions

def clab_usage() -> None:
  print("""
Usage:

    netlab clab <action> <parameters>

The 'netlab clab' command can execute the following actions:

tarball   Create a tar archive from the current clab/device configuration
build     Build a routing daemon Docker container
        
Use 'netlab clab <action> --help' to get action-specific help
""")
