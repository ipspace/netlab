#!/bin/bash
#
# Run netlab interface setup scripts before starting BIRD.
# EVPN/VXLAN configs reference kernel tunnel devices that must exist first;
# starting BIRD too early triggers a known segfault (BIRD issue #423).
#
set -e

wait_for_interfaces() {
  local timeout="${NETLAB_INTERFACE_WAIT:-30}"
  local waited=0

  while [ "$waited" -lt "$timeout" ]; do
    if [ -d /sys/class/net/eth1 ]; then
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done

  echo "Timeout waiting for containerlab interfaces (eth1)" >&2
  return 1
}

if [ -d /etc/config ] && compgen -G '/etc/config/[0-9]*-*.sh' > /dev/null; then
  wait_for_interfaces
  for script in /etc/config/[0-9]*-*.sh; do
    [ -f "$script" ] || continue
    bash "$script"
  done
fi

exec bird -f -c /etc/bird/bird.conf -d
