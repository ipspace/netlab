#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Create initial bootstrap virtual disk
cd $SCRIPT_DIR
sudo ./make-config.sh juniper.conf /tmp/vptx.bootstrap.qcow2
