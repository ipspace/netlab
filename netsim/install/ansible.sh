#!/bin/bash
#
set -e
REPLACE="--upgrade"
IGNORE="--ignore-installed"
#
# Install Python components
#
echo "Install baseline Python components"
$SUDO pip3 install $REPLACE $IGNORE $FLAG_PIP pip
$SUDO python3 -m pip install $REPLACE $IGNORE $FLAG_PIP pyopenssl cryptography
$SUDO python3 -m pip install $REPLACE $IGNORE $FLAG_PIP testresources pyyaml httplib2
$SUDO python3 -m pip install $REPLACE $IGNORE $FLAG_PIP jinja2 six bracket-expansion netaddr rich
#
echo "Install Ansible Python dependencies"
echo ".. pynacl lxml"
$SUDO python3 -m pip install $REPLACE $IGNORE $FLAG_PIP pynacl lxml
echo ".. paramiko netmiko ansible-pylibssh"
$SUDO python3 -m pip install $REPLACE $FLAG_PIP paramiko netmiko ansible-pylibssh ncclient
#
echo "Install optional Python components"
$SUDO python3 -m pip install $REPLACE $FLAG_PIP textfsm ttp jmespath ntc-templates
#
echo "Install nice-to-have Python software"
$SUDO python3 -m pip install $REPLACE $FLAG_PIP yamllint yq
#
# Install latest Ansible version with pip
#
echo "Installing Ansible"
$SUDO python3 -m pip install $REPLACE $FLAG_PIP 'ansible<=11.10'
#
echo
echo "Installation complete. Let's test Ansible version"
echo
if [[ -z "$FLAG_USER" ]]; then
  ansible-playbook --version
else
  ~/.local/bin/ansible-playbook --version
fi
