#!/bin/bash
for host in s1 s2; do
  vagrant ssh ${host} -c "cd server-${host}; /nl/netlab down --cleanup --force"
done
