# 'netsim clab' actions

def libvirt_usage() -> None:
  print("""
Usage:

    netlab libvirt <action> <parameters>

The 'netlab libvirt' command can execute the following actions:

package   Help you create a Vagrant box from a qcow/vmdk virtual disk
config    Print the build recipe for the specified Vagrant box
remove    Remove the specified Vagrant box or related libvirt volumes
        
Use 'netlab libvirt <action> --help' to get action-specific help
""")
