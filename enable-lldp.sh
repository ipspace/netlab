#!/bin/bash
if [ -z "$1" ]; then
  echo 'Usage: enable-lldp <libvirt-net-name>'
  exit 1
fi
network="$1"
bridge=$(virsh net-info ${network}|grep Bridge|awk '{ print $2 }')
echo "libvirt switch ${network} is Linux bridge ${bridge}"
echo "... enabling LLDP on ${bridge}"
sudo sh -c "echo 0x4000 >/sys/class/net/${bridge}/bridge/group_fwd_mask"
