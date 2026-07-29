#!/bin/bash
#
# Install a specific version of Containerlab -- it's now set in 'netlab install' before calling this script
#
set -e
REPLACE="--upgrade"
IGNORE="--ignore-installed"
#
echo "Update the package list"
. apt-get-update.sh
echo "Install podman"
$SUDO apt-get install -y podman podman-docker
$SUDO systemctl enable --now podman.socket
$SUDO systemctl start podman.socket
#
echo "Install containerlab version $CONTAINERLAB_VERSION"
$SUDO bash "-c" "$(curl -sL https://get.containerlab.dev)" -- -v $CONTAINERLAB_VERSION
