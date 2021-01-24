#!/bin/bash
if [ -z "$1" ]; then
  echo 'Usage: connect.sh [ --debug ] <host> [ <command> ]'
  exit 1
fi
set -e
if [ "$1" = "--debug" ]; then
  debug=1
  shift
fi
ssh_host=$1
shift
data=$(ansible-inventory --host $ssh_host)
host=$(echo $data|jq -r .ansible_host)
port=$(echo $data|jq -r .ansible_port)
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
if [ $debug ]; then
  echo 1>&2 "executing ${cmd[@]}"
fi
"${cmd[@]}"
