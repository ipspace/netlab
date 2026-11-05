#!/bin/bash
#
set -e
REPLACE="--upgrade"
IGNORE="--ignore-installed"
# Check dependencies
if [[ ! `which ansible-galaxy` ]]; then
  echo "GRPC packages depend on Ansible (ansible-galaxy), aborting..."
  exit 1
fi

echo "Install gRPC Python libraries"
$SUDO python3 -m pip install $REPLACE $IGNORE $FLAG_PIP grpcio protobuf

echo "Install Nokia SR Linux and OpenConfig Ansible collections"
ansible-galaxy collection install --upgrade nokia.srlinux nokia.openconfig
