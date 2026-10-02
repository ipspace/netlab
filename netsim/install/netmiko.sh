#!/bin/bash
#
set -e
REPLACE="--upgrade"
IGNORE="--ignore-installed"
echo "Install paramiko and netmiko"
$SUDO python3 -m pip install $REPLACE $FLAG_PIP paramiko 'netmiko[par4]'
echo
echo "Installation complete."
echo
