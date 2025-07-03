#!/bin/bash
#
set -e
#
echo "Update the package list"
. apt-get-update.sh
#
echo
echo "Install common libraries and support software"
$SUDO apt-get install -y $FLAG_APT libxslt-dev libxml2-dev zlib1g-dev genisoimage
$SUDO apt-get install -y $FLAG_APT ebtables dnsmasq-base sshpass tree jq bridge-utils curl lsb-release
echo ".. common libraries installed"
echo
echo "Install libvirt packages"
$SUDO apt-get install -y $FLAG_APT libvirt-dev qemu-kvm cpu-checker virtinst
$SUDO apt-get install -y $FLAG_APT libvirt-daemon-system libvirt-clients
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
#
# Pin vagrant version to one we know works
cat <<FILE | $SUDO tee /etc/apt/preferences.d/vagrant
#
# We have to pin the vagrant version because the newer versions contain bugs that
# can completely ruin the virtualization environment, leaving stale VMs running
#
# See https://github.com/ipspace/netlab/issues/2185 and
# https://github.com/ipspace/netlab/issues/2436 for details
#
Package: vagrant
Pin: version 2.4.3-1
Pin-Priority: 1000
FILE
. apt-get-update.sh
$SUDO apt-get install -y --allow-downgrades $FLAG_APT ruby-dev ruby-libvirt vagrant=2.4.3-1
vagrant plugin install vagrant-libvirt --plugin-version=0.12.2
echo ".. vagrant installed"
echo
set +e
G="$(groups $USER|grep libvirt)"
set -e
if [[ -z "$G" ]]; then
  echo "Add user $USER to libvirt group"
  $SUDO usermod -a -G libvirt $USER
fi
