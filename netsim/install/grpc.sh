#!/bin/bash
#
set -e
# Check dependencies
if [[ ! `which ansible-galaxy` ]]; then
  echo "GRPC packages depend on Ansible (ansible-galaxy), aborting..."
  exit 1
fi

# Install Ansible grpc plug-in and its dependencies from github repo
ansible-galaxy collection install 'git+https://github.com/nokia/ansible-networking-collections.git#/grpc/'
ansible-galaxy collection install nokia.srlinux
echo
echo "We have to upgrade Ansible to release 9.5.1 or greater or it will break"
echo "Alternatively, you can manually downgrade it to release 4.10.0 or earlier"
echo
$SUDO pip3 install $REPLACE $IGNORE $FLAG_PIP 'ansible>=9.5.1'

# grpc sources contain generated pb2 file which is not compatible with newer versions of protobuf
$SUDO pip3 install $REPLACE $IGNORE $FLAG_PIP grpcio protobuf==3.20.1
exit $?
