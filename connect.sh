#!/bin/bash
connect_ssh() {
  host=$(echo $data|jq -r .ansible_host)
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
  if [ $debug ]; then
    echo 1>&2 "executing ${cmd[@]}"
  else
    echo "Connecting to host $host via SSH using port $port..."
  fi
  "${cmd[@]}"
}

connect_docker() {
  host=$(echo $data|jq -r .ansible_host)
  echo "Connecting to container $host, starting bash..."
  cmd=(docker exec -it $host bash -il)
  if [ "$@" ]; then
    cmd+=(-c $@)
  fi
  echo 1>&2 "executing ${cmd[@]}"
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
ssh_host=$1
shift
data=$(ansible-inventory --host $ssh_host)
connection=$(echo $data|jq -r .ansible_connection)
if [[ "$connection" == *docker* ]]; then
  connect_docker $@
else
  connect_ssh $@
fi
