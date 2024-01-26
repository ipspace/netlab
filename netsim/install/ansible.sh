#!/bin/bash
cat <<EOM
Ansible installation script
=====================================================================
This script installs Ansible and related Python3 packages required
to run netlab Ansible playbooks. The script was tested on
Ubuntu 20.04.

The script assumes that you already set up Python3 environment. If
that's not the case, please run "netlab install ubuntu" first.

NOTE: the script is set to abort on first error. If the installation
completed you're probably OK even though you might have seen errors
during the installation process.
=====================================================================

EOM

# Add sudo / root check - ghostinthenet 20220418
SUDO=''
if [ "$UID" != "0" ]; then
  if [ -x "$(command -v sudo)" ]; then
    SUDO=sudo PIP_ROOT_USER_ACTION=ignore
  else
    echo 'Script requires root privileges.'
    exit 1
  fi
fi

if [ ! -z $VIRTUAL_ENV ]; then
  SUDO=""
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
# Install Python components
#
echo "Install baseline Python components"
$SUDO pip3 install $REPLACE $IGNORE $FLAG_PIP pyopenssl cryptography
$SUDO pip3 install $REPLACE $IGNORE $FLAG_PIP testresources pyyaml httplib2
$SUDO pip3 install $REPLACE $IGNORE $FLAG_PIP jinja2 six bracket-expansion netaddr
#
echo "Install Ansible Python dependencies"
echo ".. pynacl lxml"
$SUDO pip3 install $REPLACE $IGNORE $FLAG_PIP pynacl lxml
echo ".. paramiko netmiko ansible-pylibssh"
$SUDO pip3 install $REPLACE $FLAG_PIP paramiko netmiko ansible-pylibssh
#
echo "Install optional Python components"
$SUDO pip3 install $REPLACE $FLAG_PIP textfsm ttp jmespath ntc-templates
#
echo "Install nice-to-have Python software"
$SUDO pip3 install $REPLACE $FLAG_PIP yamllint yq
#
# Install latest Ansible version with pip
#
echo "Installing Ansible"
$SUDO pip3 install $REPLACE $FLAG_PIP ansible
#
echo
echo "Installation complete. Let's test Ansible version"
echo
ansible-playbook --version
