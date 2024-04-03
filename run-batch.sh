#!/bin/bash
#
. vars.sh
#for dev in frr cumulus eos; do
#  run-device-provider.sh $dev clab
#done

for dev in iosv csr vptx; do
  run-device-provider.sh $dev libvirt
done

find . -name '*log' -empty -delete
git add .
git commit -m "Integration tests finished at $(date)"
git push
