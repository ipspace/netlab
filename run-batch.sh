#!/bin/bash
#
. vars.sh
for dev in frr cumulus eos; do
  run-device-provider.sh $dev clab
done

for dev in iosv csr vptx vyos; do
  run-device-provider.sh $dev libvirt
done
commit-log.sh
