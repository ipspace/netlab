#!/bin/bash

## Generic requirements
#
if ! command -v awk &>/dev/null; then
  echo "The netsim-tools connect script requires awk. Exiting."
  exit 1
fi

if ! command -v grep &>/dev/null; then
  echo "The netsim-tools connect script requires sed. Exiting."
  exit 1
fi

if ! command -v sed &>/dev/null; then
  echo "The netsim-tools connect script requires sed. Exiting."
  exit 1
fi

## Parse hosts.yml
#
# Intended for netsim-tools generated hosts.yml
# Currently the connection_type docker does not require ansible-inventory for
# this connection script to work.
# SSH users require ansible-inventory t connect to their instances.
#
# Source (CC BY-SA 3.0):
# https://stackoverflow.com/a/21189044
#
parse_hosts () {
   local prefix=$2
   local s='[[:space:]]*' w='[a-zA-Z0-9_]*' fs=$(echo @|tr @ '\034')
   sed -ne "s|^\($s\):|\1|" \
        -e "s|^\($s\)\($w\)$s:$s[\"']\(.*\)[\"']$s\$|\1$fs\2$fs\3|p" \
        -e "s|^\($s\)\($w\)$s:$s\(.*\)$s\$|\1$fs\2$fs\3|p"  $1 |
   awk -F$fs '{
      indent = length($1)/2;
      vname[indent] = $2;
      for (i in vname) {if (i > indent) {delete vname[i]}}
      if (length($3) > 0) {
         vn=""; for (i=0; i<indent; i++) {vn=(vn)(vname[i])("_")}
         printf("%s%s%s=\"%s\"\n", "'$prefix'",vn, $2, $3);
      }
   }'
}

connect_ssh() {

  if ! command -v jq &>/dev/null; then
    echo "The netsim-tools SSH connect script requires jq. Exiting."
    exit 1
  fi

  if ! command -v ansible-inventory &>/dev/null; then
    echo "The netsim-tools SSH connect script requires ansible-inventory. Exiting."
    exit 1
  fi

  if ! command -v ssh &>/dev/null; then
    echo "The netsim-tools SSH connect script requires ssh. Exiting."
    exit 1
  fi

  data=$(ansible-inventory --host $id)
  port=$(echo $data|jq -e -r .ansible_port) || port=22
  user=$(echo $data|jq -r .ansible_user)
  pass=$(echo $data|jq -r .ansible_ssh_pass)
  cmd=(ssh -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' -o "LogLevel ERROR")
  if [ $port ]; then
    cmd+=(-p $port)
  fi
  if [ -n "$user" ]; then
    host="$user@$host"
  fi
  if [ -n "$pass" ]; then
    cmd=(sshpass -p $pass "${cmd[@]}")
  fi
  cmd+=($host)
  cmd+=($@)
  echo "Connecting to host $host via SSH using port $port..."
  if [ $debug ]; then
    echo 1>&2 "executing ${cmd[@]}"
  fi
  "${cmd[@]}"
}

connect_docker() {

  if ! command -v docker &>/dev/null; then
    echo "The netsim-tools container connect script requires docker. Exiting."
    exit 1
  fi

  echo "Connecting to container $host via docker, starting bash..."
  cmd=(docker exec -it $host bash -il -c)
  if [ $# -gt 0 ]; then
    cmd_usr="$@"
    cmd+=("$cmd_usr")
  fi
  if [ $debug ]; then
    echo 1>&2 "executing ${cmd[@]}"
  fi
  "${cmd[@]}"
}

if [ -z "$1" ]; then
  echo 'Usage: connect.sh [ --debug ] <host> [ <command> ]'
  exit 1
fi
set -e
if [ "$1" = "--debug" ]; then
  debug=1
  shift
fi
id=$1
shift
host=$(parse_hosts hosts.yml | grep -E "hosts\_$id\_ansible\_host=\"(.*)-$id\"" | cut -d= -f2)
host="${host%\"}"
host="${host#\"}"
if parse_hosts hosts.yml | grep "hosts\_$id\_connection\_type=\"docker\"" ; then
  connect_docker $@
else
  connect_ssh $@
fi
