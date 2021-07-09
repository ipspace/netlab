#!/bin/bash
cat <<EOM
Libvirt/Ubuntu Installation Script
=====================================================================
This script installs Libvirt, Vagrant, and vagrant-libvirt plugin
on a Ubuntu system. The script was tested on Ubuntu 20.04.

NOTE: the script is set to abort on first error. If the installation
completed you're probably OK even though you might have seen errors
during the installation process.
=====================================================================

EOM
if [[ -z "$FLAG_YES" ]]; then
  read -p "Are you sure you want to proceed [Y/n] " -n 1 -r
  echo
  FLAG_YES="$REPLY"
fi
if [[ ! $FLAG_YES =~ ^[Yy]$ ]]; then
  echo "Aborting..."
  exit 1
fi
set -e
#
echo "Update the package list"
sudo apt-get $FLAG_QUIET update
#
echo
echo "Install common libraries and support software"
sudo apt-get install -y $FLAG_QUIET libxslt-dev libxml2-dev zlib1g-dev
sudo apt-get install -y $FLAG_QUIET ebtables dnsmasq-base sshpass tree jq bridge-utils
echo ".. common libraries installed"
echo
echo "Install libvirt packages"
sudo apt-get install -y $FLAG_QUIET libvirt-dev qemu qemu-kvm virtinst
sudo apt-get install -y $FLAG_QUIET libvirt-daemon-system libvirt-clients
echo ".. libvirt packages installed"
echo
echo "Install vagrant"
sudo apt-get install -y $FLAG_QUIET ruby-dev ruby-libvirt vagrant
set +e
PLUGIN_VER=$(vagrant plugin list|grep vagrant-libvirt|grep 0.4.1)
set -e
if [[ -z "$PLUGIN_VER" ]]; then
  vagrant plugin install vagrant-libvirt --plugin-version=0.4.1
else
  echo ".. libvirt-vagrant plugin already installed"
fi
echo ".. vagrant installed"
echo
set +e
GROUPS="$(groups|grep libvirt)"
set -e
if [[ -z "$GROUPS" ]]; then
  echo "Add vagrant user to libvirt group"
  sudo usermod -a -G libvirt vagrant
  echo ".. You might need to log out and log in to start using netsim-tools with libvirt"
  echo
fi
echo "Create vagrant-libvirt virtual network"
set +e
NET_LIST=$(sudo virsh net-list --all|grep vagrant-libvirt)
if [[ -n "$NET_LIST" ]]; then
  echo ".. removing existing vagrant-libvirt network"
  sudo virsh net-destroy vagrant-libvirt
  sudo virsh net-undefine vagrant-libvirt
fi
SCRIPT_DIR=$(dirname "${BASH_SOURCE[0]}")
set -e
sudo virsh net-define "$SCRIPT_DIR/../templates/provider/libvirt/vagrant-libvirt.xml"
echo ".. vagrant-libvirt network created"
