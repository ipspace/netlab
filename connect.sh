#!/bin/bash
if [ -z "$1" ]; then
  echo 'Usage: connect.sh <host>'
  exit 1
fi
set -e
data=$(ansible-inventory --host $1)
host=$(echo $data|jq -r .ansible_host)
user=$(echo $data|jq -r .ansible_user)
pass=$(echo $data|jq -r .ansible_ssh_pass)
cmd=(ssh -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' -o "LogLevel ERROR")
if [ -n "$user" ]; then
  host="$user@$host"
fi
if [ -n "$pass" ]; then
  cmd=(sshpass -p $pass "${cmd[@]}")
fi
cmd+=($host)
echo "executing ${cmd[@]}"
"${cmd[@]}"
