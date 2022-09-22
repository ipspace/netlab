#!/bin/bash

set -e  # Quit on error

DEVICE=${1:-"srlinux"}

function can_ping() {
 local host=$1
 local ip=$2
 docker exec -it clab-${host} ping -c2 $ip
}

function cant_ping() {
 local host=$1
 local ip=$2

 set +e
 docker exec -it clab-${host} ping -W1 -c2 $ip
 if [ $? != 1 ]; then
  echo "Error: ${host} should not be able to ping ${ip}"
  exit 1
 fi
 set -e
}


# Runs a bunch of integration test cases, and performs ping checks to validate the setup
netlab up -d "${DEVICE}" -p clab "vlan/vlan-bridge-native.yml"

can_ping  "vlan-h1" "172.16.0.2"
can_ping  "vlan-h3" "172.16.1.4"
cant_ping "vlan-h1" "172.16.1.3"

netlab down

exit $?