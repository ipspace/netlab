#!/bin/bash
status=0
for port in 2001 2002; do
  echo "Checking SSH port forwarding on port $port"
  if ! (sshpass -p admin \
    ssh -p $port \
      -o UserKnownHostsFile=/dev/null \
      -o StrictHostKeyChecking=no \
      -o LogLevel=ERROR \
      admin@127.0.0.1 show ver | grep EOS >/dev/null && echo "Forwarding on port $port works"); then
    echo "Forwarding on port $port failed"
    status=1
  fi
done

echo "Checking HTTP port forwarding on 8080"
if ! (curl -s http://localhost:8080 >/dev/null && echo "HTTP port forwarding works"); then
  echo "HTTP forwarding to R1 failed"
  status=1
fi

exit $status
