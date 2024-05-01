#!/bin/bash
#
. vars.sh
export NETLAB_DEVICE=$1
shift
export NETLAB_PROVIDER=$1
shift
export MODULE=$1
shift
if [[ -z $1 ]]; then
  echo "Usage: redo.sh device provider suite test-pattern"
  exit
fi
LOG_PATH=$CICD_LOG_PATH/$NETLAB_DEVICE/$NETLAB_PROVIDER/$MODULE
for limit in $@; do
  pushd $(realpath "$CICD_TEST_PATH") >/dev/null
  echo "Starting device $NETLAB_DEVICE provider $NETLAB_PROVIDER module $MODULE limit $limit logging on $LOG_PATH"
  ./device-module-test $MODULE --workdir ${NETLAB_WORKDIR:-/tmp/netlab_cicd} --logdir "$LOG_PATH" --batch --redo $limit
  popd >/dev/null
done
