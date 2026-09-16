#!/bin/bash
for host in s1 s2; do
  vagrant ssh $host -c "rm -rv server-${host}; sudo ip link set dev ens5 mtu 9000"
  vagrant scp ../server-${host} ${host}:
  vagrant ssh ${host} -c "cd server-${host}; /nl/netlab up --snapshot"
done
