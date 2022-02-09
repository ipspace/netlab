#!/bin/bash
cat <<EOM
Docker/Containerlab Installation Script
=====================================================================
This script installs Docker and containerlab on a Ubuntu system.
The script was tested on Ubuntu 20.04.

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
set +e
sudo rm /usr/share/keyrings/docker-archive-keyring.gpg 2>/dev/null
set -e
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
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
