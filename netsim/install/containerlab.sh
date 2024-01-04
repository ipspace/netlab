#!/bin/bash

# Install a specific version of Containerlab
CONTAINERLAB_VERSION="0.49.0"

cat <<EOM
Docker/Containerlab Installation Script
=====================================================================
This script installs Docker and containerlab on a Debian or Ubuntu
system. The script was tested on Debian 11.3 and Ubuntu 20.04.

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
REPLACE="--upgrade"
IGNORE="--ignore-installed"
#
echo "Update the package list"
$SUDO apt-get $FLAG_QUIET update
#
echo
echo "Install support software"
$SUDO apt-get install -y $FLAG_QUIET ca-certificates curl gnupg lsb-release
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
  echo ".. You might need to log out and log in if you want to use Docker commands"
  echo
fi
cat <<EOM

=====================================================================
Docker and Containerlab were successfully installed.

To test the installation:

* Log out
* Log back in
* Run 'netlab test clab'
=====================================================================
EOM
