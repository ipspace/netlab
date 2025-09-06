#!/bin/bash
#
set -e
#
# Comment the next line if you want to have verbose installation messages
#
echo "Update package list and upgrade the existing packages"
. apt-get-update.sh
echo "Installing GraphViz"
$SUDO apt-get -y $FLAG_APT install graphviz
echo "Installing D2"
curl -fsSL https://d2lang.com/install.sh | sh -s --
