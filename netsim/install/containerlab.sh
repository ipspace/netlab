#!/bin/bash
#
# Install a specific version of Containerlab -- it's now set in 'netlab install' before calling this script
# CONTAINERLAB_VERSION="0.62.2"
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

set +e
$SUDO rm /usr/share/keyrings/docker-archive-keyring.gpg 2>/dev/null
# Re-referenced to default APT GPG keyring directory - ghostinthenet - 20220417
$SUDO rm /etc/apt/trusted.gpg.d/docker-archive-keyring.gpg 2>/dev/null
set -e
# Added DISTRIBUTION variable and re-referenced to default APT GPG keyring directory - ghostinthenet - 20220417
curl -fsSL https://download.docker.com/linux/$DISTRIBUTION/gpg | $SUDO gpg --dearmor -o /etc/apt/trusted.gpg.d/docker-archive-keyring.gpg
# Added DISTRIBUTION variable and removed custom APT GPG keychain source - ghostinthenet - 20220417
echo "deb [arch=$(dpkg --print-architecture)] https://download.docker.com/linux/$DISTRIBUTION $(lsb_release -cs) stable" | $SUDO tee /etc/apt/sources.list.d/docker.list > /dev/null
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
