#!/bin/bash
cat <<EOM
Libvirt/Ubuntu Installation Script
=====================================================================
This script installs Libvirt, Vagrant, and vagrant-libvirt plugin
on a Ubuntu system. The script was tested on Debian 11.3 and Ubuntu
20.04.

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
echo "Update the package list"
$SUDO apt-get $FLAG_QUIET update
#
echo
echo "Install common libraries and support software"
$SUDO apt-get install -y $FLAG_QUIET libxslt-dev libxml2-dev zlib1g-dev genisoimage
$SUDO apt-get install -y $FLAG_QUIET ebtables dnsmasq-base sshpass tree jq bridge-utils
echo ".. common libraries installed"
echo
echo "Install libvirt packages"
$SUDO apt-get install -y $FLAG_QUIET libvirt-dev qemu qemu-kvm virtinst
$SUDO apt-get install -y $FLAG_QUIET libvirt-daemon-system libvirt-clients
echo ".. libvirt packages installed"
echo
echo "Install vagrant"
echo ".. setting up Vagrant repository"
set +e
$SUDO rm /etc/apt/trusted.gpg.d/hashicorp-security.gpg 2>/dev/null
$SUDO rm /etc/apt/sources.list.d/vagrant.list 2>/dev/null
set -e
# add-apt-repository has been deprecated, doesn't work on Debian 11 and will be removed from Ubuntu 22
# changed to new method - ghostinthenet - 20220417
curl -fsSL https://apt.releases.hashicorp.com/gpg | $SUDO gpg --dearmor -o /etc/apt/trusted.gpg.d/hashicorp-security.gpg
$SUDO sh -c 'echo "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main" > /etc/apt/sources.list.d/vagrant.list'
$SUDO apt-get update
$SUDO apt-get install -y $FLAG_QUIET ruby-dev ruby-libvirt vagrant=2.4.0-1
vagrant plugin install vagrant-libvirt --plugin-version=0.12.2
echo ".. vagrant installed"
echo
set +e
G="$(groups $USER|grep libvirt)"
set -e
if [[ -z "$G" ]]; then
  echo "Add user $USER to libvirt group"
  $SUDO usermod -a -G libvirt $USER
  echo ".. You might need to log out and log in to start using netlab with libvirt"
  echo
fi
#echo "Create vagrant-libvirt virtual network"
#set +e
#NET_LIST=$($SUDO virsh net-list --all|grep vagrant-libvirt)
#if [[ -n "$NET_LIST" ]]; then
#  echo ".. removing existing vagrant-libvirt network"
#  $SUDO virsh net-destroy vagrant-libvirt
#  $SUDO virsh net-undefine vagrant-libvirt
#fi
#SCRIPT_DIR=$(dirname "${BASH_SOURCE[0]}")
#set -e
#$SUDO virsh net-define "$SCRIPT_DIR/../templates/provider/libvirt/vagrant-libvirt.xml"
#echo ".. vagrant-libvirt network created"
#$SUDO virsh net-start vagrant-libvirt
#$SUDO virsh net-autostart vagrant-libvirt
