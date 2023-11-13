#!/bin/bash
cat <<EOM
Ubuntu Packages Installation Script
=====================================================================
This script updates your system, installs additional APT packages,
and nice-to-have tools like git, jq...

NOTE: the script is set to abort on first error. If the installation
completed you're probably OK even though you might have seen errors
during the installation process.
=====================================================================

EOM

# If we have sudo command, then we use it to set environment variables
if [ -x "$(command -v sudo)" ]; then
  SUDO='sudo DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a'
else
#
# no sudo command, if we're not root we can't proceed
  SUDO=""
  if [ "$UID" != "0" ]; then
    echo 'Script requires root privileges.'
    exit 0
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
$SUDO apt-get -y $FLAG_APT install build-essential python3-dev libffi-dev
echo "Installing XML libraries"
$SUDO apt-get -y $FLAG_APT install libxslt1-dev libssl-dev
echo
echo "Installation complete."
echo
