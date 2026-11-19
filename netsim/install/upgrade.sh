#!/bin/bash
#
set -e
echo "Upgrade networklab package"
$SUDO "$PYTHON" -m pip install --upgrade $FLAG_PIP networklab
echo
echo "Upgrade complete."
echo
