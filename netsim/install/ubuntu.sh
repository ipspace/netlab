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

# Add sudo / root check - ghostinthenet 20220418
SUDO='DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a'
if [ "$UID" != "0" ]; then
 if [ -x "$(command -v sudo)" ]; then
  SUDO="sudo $SUDO"
 else
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
# Added curl, which is not installed by default on Debian - ghostinthenet - 20220417
$SUDO apt-get -y $FLAG_APT install python3 python3-setuptools ifupdown python3-pip curl
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
