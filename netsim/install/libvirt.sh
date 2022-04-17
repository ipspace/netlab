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
if [[ -z "$FLAG_YES" ]]; then
  read -p "Are you sure you want to proceed [Y/n] " -n 1 -r
  echo
  # Added curl, which is not installed by default on Debian - ghostinthenet - 20220417
  if ! [[ $REPLY =~ ^$|[Yy] ]]; then
   echo "Aborting..."
   exit 1
  fi
  FLAG_YES="Y"
fi
#
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
echo ".. setting up Vagrant repository"
set +e
sudo rm /etc/apt/trusted.gpg.d/hashicorp-security.gpg 2>/dev/null
sudo rm /etc/apt/sources.list.d/vagrant.list 2>/dev/null
set -e
# add-apt-repository has been deprecated, doesn't work on Debian 11 and will be removed from Ubuntu 22
# changed to new method - ghostinthenet - 20220417
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/hashicorp-security.gpg
sudo echo "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main" > /etc/apt/sources.list.d/vagrant.list
sudo apt-get update
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
G="$(groups $USER|grep libvirt)"
set -e
if [[ -z "$G" ]]; then
  echo "Add user $USER to libvirt group"
  sudo usermod -a -G libvirt $USER
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
sudo virsh net-start vagrant-libvirt
sudo virsh net-autostart vagrant-libvirt
