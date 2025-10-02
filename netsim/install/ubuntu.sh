#!/bin/bash
#
set -e
#
# Comment the next line if you want to have verbose installation messages
#
echo "Update package list and upgrade the existing packages"
. apt-get-update.sh
$SUDO apt-get upgrade -y $FLAG_APT
#
# Install missing packages
#
echo "Install missing packages (also a pretty long operation)"
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
# Add linux-modules-extra for e.g. vrf
# linux-modules-extra-$(uname -r) should exist, but it won't if we're running
# on a kernel that has been purged from the package server; in that case the
# user will likely need to reboot.
EXTRA="linux-modules-extra-$(uname -r)"
if [ -n "$(apt-cache search $EXTRA)" ]; then
  echo "Installing additional Linux kernel modules"
  $SUDO apt-get -y $FLAG_APT install $EXTRA
fi
