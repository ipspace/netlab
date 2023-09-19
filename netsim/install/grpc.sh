#!/bin/bash

# Check dependencies
if [[ ! `which ansible-galaxy` ]]; then
  echo "GRPC packages depend on Ansible (ansible-galaxy), aborting..."
  exit 1
fi

# Add sudo / root check
SUDO=''
if [ "$UID" != "0" ]; then
  if [ -x "$(command -v sudo)" ]; then
    SUDO=sudo
  else
    echo 'Script requires root privileges.'
    exit 1
  fi
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

# The last version of Ansible working with Nokia Ansible collection is 4.10.0
#
sudo python3 -m pip install --upgrade ansible==4.10.0

# grpc sources contain generated pb2 file which is not compatible with newer versions of protobuf
python3 -m pip install grpcio protobuf==3.20.1 --upgrade

exit $?
