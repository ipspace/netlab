#!/bin/bash
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
if [[ -z "$FLAG_YES" ]]; then
  read -p "Are you sure you want to proceed [Y/n] " -n 1 -r
  echo
  # Original script didn't properly accept an empty response as a default Y - ghostinthenet - 20220417
  if ! [[ $REPLY =~ ^$|[Yy] ]]; then
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
sudo apt-get $FLAG_QUIET update
#
echo
echo "Install support software"
sudo apt-get install -y $FLAG_QUIET ca-certificates curl gnupg lsb-release
echo "Install Docker GPG key and set up Docker repository"
# Begin code to identify distribution and populate DISTRIBUTION variable - ghostinthenet - 20220417
if [ -f /etc/debian_version ]; then
 if [ -f /etc/lsb-release ]; then
  if [[ $(grep DISTRIB_ID /etc/lsb-release | awk -F'=' '{print $2;}') == 'Ubuntu' ]]; then
   DISTRIBUTION='ubuntu'
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
sudo rm /usr/share/keyrings/docker-archive-keyring.gpg 2>/dev/null
# Re-referenced to default APT GPG keyring directory - ghostinthenet - 20220417
sudo rm /etc/apt/trusted.gpg.d/docker-archive-keyring.gpg 2>/dev/null
set -e
# Added DISTRIBUTION variable and re-referenced to default APT GPG keyring directory - ghostinthenet - 20220417
curl -fsSL https://download.docker.com/linux/$DISTRIBUTION/gpg | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/docker-archive-keyring.gpg
# Added DISTRIBUTION variable and removed custom APT GPG keychain source - ghostinthenet - 20220417
echo "deb [arch=$(dpkg --print-architecture)] https://download.docker.com/linux/$DISTRIBUTION $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
#
echo "Install Docker Engine"
sudo apt-get update
sudo apt-get install -y $FLAG_QUIET docker-ce docker-ce-cli containerd.io
echo "Install containerlab"
sudo bash -c "$(curl -sL https://get-clab.srlinux.dev)"
set +e
G="$(groups $USER|grep docker)"
set -e
if [[ -z "$G" ]]; then
  echo "Add user $USER to docker group"
  sudo usermod -a -G docker $USER
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
