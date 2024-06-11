#!/bin/bash
cat <<EOM
Nokia GRPC installation script
=====================================================================
This script installs Nokia Ansible Galaxy GRPC plug-in and related
Python3 packages. The script was tested on Ubuntu 22.04.

The script assumes that you already set up Python3 environment. If
that's not the case, please run "netlab install ubuntu" first.

NOTE: the script is set to abort on first error. If the installation
completed you're probably OK even though you might have seen errors
during the installation process.
=====================================================================

EOM
set -e
# Check dependencies
if [[ ! `which ansible-galaxy` ]]; then
  echo "GRPC packages depend on Ansible (ansible-galaxy), aborting..."
  exit 1
fi

if [[ -z "$FLAG_YES" ]]; then
  # Remove implied default of Y - ghostinthenet 20220418
  read -p "Are you sure you want to proceed [y/n]: " -n 1 -r
  echo
  if ! [[ $REPLY =~ [Yy] ]]; then
    echo "Aborting..."
    exit 1
  fi
  FLAG_YES="Y"
fi

# Install Ansible grpc plug-in and its dependencies from github repo
ansible-galaxy collection install 'git+https://github.com/nokia/ansible-networking-collections.git#/grpc/'
echo
echo "We have to upgrade Ansible to release 9.5.1 or greater or it will break"
echo "Alternatively, you can manually downgrade it to release 4.10.0 or earlier"
echo
$SUDO pip3 install $REPLACE $IGNORE $FLAG_PIP 'ansible>=9.5.1'

# grpc sources contain generated pb2 file which is not compatible with newer versions of protobuf
$SUDO pip3 install $REPLACE $IGNORE $FLAG_PIP grpcio protobuf==3.20.1

cat <<EOM
=====================================================================
GRPC plug-in and related Python libraries were installed.

To test the installation, run 'netlab test grpc'
=====================================================================
EOM

exit $?
