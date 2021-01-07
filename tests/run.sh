#!/bin/bash
set -e
TOOLS="$( cd "$(dirname ${BASH_SOURCE[0]})/.." && pwd)"
echo "Using netsim-tools from $TOOLS"
PATH=$TOOLS:$PATH
rm -fr host_vars group_vars
create-topology -g -i -c
vagrant up
echo
echo "Sleeping for 60 seconds - Nexus OS is slow to realize it has an Ethernet module"
sleep 60
initial-config.ansible
collect-configs.ansible
echo
echo "Looks like everything worked. Destroy the setup with vagrant destroy --force"
