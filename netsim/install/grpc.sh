#!/bin/bash

# Check dependencies
if [[ ! `which ansible-galaxy` ]]; then
  echo "GRPC packages depend on Ansible (ansible-galaxy), aborting..."
  exit 1
fi

if [[ -z "$FLAG_YES" ]]; then
  # Remove implied default of Y - ghostinthenet 20220418
  read -p "Are you sure you want to proceed [y/n] " -n 1 -r
  echo
  if ! [[ $REPLY =~ [Yy] ]]; then
    echo "Aborting..."
    exit 1
  fi
  FLAG_YES="Y"
fi

# Install Ansible grpc plug-in and its dependencies from github repo
ansible-galaxy collection install 'git+https://github.com/nokia/ansible-networking-collections.git#/grpc/'

# grpc sources contain generated pb2 file which is not compatible with newer versions of protobuf
python3 -m pip install grpcio protobuf==3.20.1 --upgrade

exit $?
