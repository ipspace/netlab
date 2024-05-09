#!/bin/bash
#
. vars.sh
set +e
for dev in frr cumulus eos srlinux vyos; do
  run-device-provider.sh $dev clab $@
done

for dev in iosv csr nxos vptx vyos arubacx routeros7 dellos10; do
  run-device-provider.sh $dev libvirt $@
done
if [[ -z $1 ]]; then
  commit-log.sh
else
  echo "Not committing the results, do the commit manually"
fi
