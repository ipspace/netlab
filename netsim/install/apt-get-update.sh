#!/bin/bash
#
retry=6
sleep=${APT_WAIT:-10}
echo "Updating APT package lists"
until $SUDO apt-get $FLAG_QUIET -y update >/dev/null; do
  echo "Cannot update APT lists, another process is working on them. Retrying in $sleep seconds"
  sleep $sleep
  if ! ((retry=retry-1)); then
    echo
    echo "I waited long enough, I'm giving up"
    exit 1
  fi
done
