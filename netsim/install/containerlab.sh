#!/bin/bash
#
# Install a specific version of Containerlab
CONTAINERLAB_VERSION="0.62.2"
#
set -e
REPLACE="--upgrade"
IGNORE="--ignore-installed"
#
echo "Update the package list"
$SUDO apt-get $FLAG_QUIET update
#
echo
echo "Install support software"
$SUDO apt-get install -y $FLAG_QUIET ca-certificates curl gnupg lsb-release iptables
echo "Install Docker GPG key and set up Docker repository"

# Begin code to identify distribution and populate DISTRIBUTION variable - ghostinthenet - 20220417
if [ -f /etc/debian_version ]; then
 if [ -f /etc/lsb-release ]; then
  if [[ $(grep DISTRIB_ID /etc/lsb-release | awk -F'=' '{print $2;}') == 'Ubuntu' ]]; then
   DISTRIBUTION='ubuntu'
  # Exit if lsb-release distribution ID isn't Ubuntu - ghostinthenet 20220418
  else
   echo "Installed distribution is an untested Ubuntu derivative..."
   exit 1
  fi
 else
  DISTRIBUTION='debian'
 fi
else
 echo 'Installed distribution is neither Debian nor Ubuntu. Aborting...'
 exit 1
fi

# End code to identify distribution and populate DISTRIBUTION variable - ghostinthenet - 20220417
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
$SUDO apt-get update
$SUDO apt-get install -y $FLAG_QUIET docker-ce docker-ce-cli containerd.io
echo "Install containerlab version $CONTAINERLAB_VERSION"
$SUDO bash "-c" "$(curl -sL https://get.containerlab.dev)" -- -v $CONTAINERLAB_VERSION
set +e
G="$(groups $USER|grep docker)"
set -e
if [[ -z "$G" ]]; then
  echo "Add user $USER to docker group"
  $SUDO usermod -a -G docker $USER
fi
