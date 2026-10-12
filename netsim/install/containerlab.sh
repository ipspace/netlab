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
#
echo
echo "Install support software"
$SUDO apt-get install -y $FLAG_APT ca-certificates curl gnupg lsb-release iptables
echo "Install Docker GPG key and set up Docker repository for $DISTRIBUTION"

#
# Remove the repository definition and the keys created by the previous versions of this script.
# The old docker.list has to go: APT complains about a repository configured multiple times.
#
$SUDO rm -f /etc/apt/sources.list.d/docker.list
$SUDO rm -f /usr/share/keyrings/docker-archive-keyring.gpg /etc/apt/trusted.gpg.d/docker-archive-keyring.gpg
#
# Docker repository in the deb822 format, with the key usable only for that repository
# (see https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository)
#
$SUDO install -m 0755 -d /etc/apt/keyrings
$SUDO curl -fsSL https://download.docker.com/linux/$DISTRIBUTION/gpg -o /etc/apt/keyrings/docker.asc
$SUDO chmod a+r /etc/apt/keyrings/docker.asc
$SUDO tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/$DISTRIBUTION
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
#
echo "Install Docker Engine"
. apt-get-update.sh
$SUDO apt-get install -y $FLAG_APT docker-ce docker-ce-cli containerd.io
echo "Install containerlab version $CONTAINERLAB_VERSION"
$SUDO bash "-c" "$(curl -sL https://get.containerlab.dev)" -- -v $CONTAINERLAB_VERSION
set +e
G="$(groups $USER|grep docker)"
set -e
if [[ -z "$G" ]]; then
  echo "Add user $USER to docker group"
  $SUDO usermod -a -G docker $USER
fi
