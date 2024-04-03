#!/bin/bash
#

TEST_PATH="~/net101/tools/tests/integration/"

run_device_test() {
  LOG_PATH="$(pwd)/$1/$2/$mod"
  rm -r "$LOG_PATH"
  pushd ~/net101/tools/tests/integration/
  ./device-module-test -d $1 -p $2 $mod --workdir /tmp/netlab_cicd --logdir "$LOG_PATH" --batch
  popd
}

run_device() {
  for mod in initial ospf/ospfv2 ospf/ospfv3 bgp vrf vxlan; do
    run_device_test $1 $2 $mod
  done
  exit
}

for dev in frr cumulus eos; do
  run_device $dev clab
done

for dev in iosv csr vptx; do
  run_device $dev libvirt
done

