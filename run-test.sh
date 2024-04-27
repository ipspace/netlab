#!/bin/bash
#
. vars.sh
if [[ -z $NETLAB_DEVICE ]]; then
  echo "NETLAB_DEVICE is not set, aborting"
  exit
fi

if [[ -z $NETLAB_PROVIDER ]]; then
  echo "NETLAB_PROVIDER is not set, aborting"
  exit
fi

MODULE=$1
FEATURE=${2:-$1}
LOG_PATH=$CICD_LOG_PATH/$NETLAB_DEVICE/$NETLAB_PROVIDER/$MODULE
if [ "$FEATURE" != "skip" ]; then
  echo "Checking feature $FEATURE for module $MODULE"
  netlab show defaults devices.$NETLAB_DEVICE.features.$FEATURE >/dev/null 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "Feature $FEATURE is not supported by device $NETLAB_DEVICE, skipping tests"
    exit
  fi
fi

rm -r "$LOG_PATH"
pushd $(realpath "$CICD_TEST_PATH") >/dev/null
echo "Starting device $NETLAB_DEVICE provider $NETLAB_PROVIDER module $1 logging on $LOG_PATH"
./device-module-test $1 --workdir /tmp/netlab_cicd --logdir "$LOG_PATH" --batch
popd >/dev/null
