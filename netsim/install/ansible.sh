#!/bin/bash
cat <<EOM
Ansible installation script
=====================================================================
This script installs Ansible and related Python3 packages required
to run netsim-tools Ansible playbooks. The script was tested on
Ubuntu 20.04.

The script assumes that you already set up Python3 environment. If
that's not the case, please run "netlab install ubuntu" first.

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
#
set -e
REPLACE="--upgrade"
IGNORE="--ignore-installed"
#
# Install Python components
#
echo "Install baseline Python components"
sudo pip3 install $REPLACE $IGNORE $FLAG_PIP testresources pyyaml httplib2
sudo pip3 install $REPLACE $IGNORE $FLAG_PIP jinja2 six bracket-expansion netaddr
#
echo "Install Ansible Python dependencies"
echo ".. pynacl lxml"
sudo pip3 install $REPLACE $IGNORE $FLAG_PIP pynacl lxml
echo ".. paramiko netmiko"
sudo pip3 install $REPLACE $FLAG_PIP paramiko netmiko
#
echo "Install optional Python components"
sudo pip3 install $REPLACE $FLAG_PIP textfsm ttp jmespath ntc-templates
#
echo "Install nice-to-have Python software"
sudo pip3 install $REPLACE $FLAG_PIP yamllint yq
#
# Install latest Ansible version with pip
#
echo "Installing Ansible"
sudo pip3 install $REPLACE $FLAG_PIP ansible
#
echo
echo "Installation complete. Let's test Ansible version"
echo
ansible-playbook --version
