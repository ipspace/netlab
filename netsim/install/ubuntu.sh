#!/bin/bash
#
set -e
#
# Comment the next line if you want to have verbose installation messages
#
echo "Update package list and upgrade the existing packages"
$SUDO apt-get update -y $FLAG_QUIET 
$SUDO apt-get upgrade -y $FLAG_APT
#
# Install missing packages
#
echo "Install missing packages (also a pretty long operation)"
# Add linux-modules-extra for e.g. vrf
# linux-modules-extra-$(uname -r) should exist, but it won't if we're running
# on a kernel that has been purged from the package server; in that case the
# user will likely need to reboot.
EXTRA=""
if apt-cache show linux-modules-extra-$(uname -r) > /dev/null; then
  EXTRA="linux-modules-extra-$(uname -r)"
fi
# Added curl, which is not installed by default on Debian - ghostinthenet - 20220417
$SUDO apt-get -y $FLAG_APT install python3 python3-setuptools ifupdown python3-pip curl $EXTRA
echo "Install nice-to-have packages"
$SUDO apt-get -y $FLAG_APT install git ack-grep jq tree sshpass colordiff
#
# Install Ansible and NAPALM dependencies
#
echo "Install Python development and build modules"
$SUDO apt-get -y $FLAG_APT install build-essential python3-dev libffi-dev libssh-dev
echo "Installing XML libraries"
$SUDO apt-get -y $FLAG_APT install libxslt1-dev libssl-dev
