#!/bin/bash
#
. vars.sh
usage() {
  echo
  echo 'Usage: run-device-provider $device $provider'
  exit
}

if [[ -z $1 ]]; then
  echo 'Device not specified'
  usage
fi

if [[ -z $2 ]]; then
  echo 'Provider not specified'
  usage
fi

export NETLAB_DEVICE=$1
export NETLAB_PROVIDER=$2
export PATH=.:$PATH
shift
shift
if [[ -n $@ ]]; then
  for mod in $@; do
    run-test.sh $mod
  done
  exit
fi
run-test.sh initial
run-test.sh ospf/ospfv2 ospf
run-test.sh ospf/ospfv3 ospf
run-test.sh bgp
run-test.sh vrf
run-test.sh vlan
run-test.sh vxlan
run-test.sh dhcp
