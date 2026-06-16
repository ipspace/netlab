FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

LABEL maintainer="Netlab project <netlab.tools>"
LABEL description="BIRD Internet Routing Daemon (bird.network.cz)"

RUN mkdir /etc/bird && mkdir /run/bird && apt-get update && apt-get install -y iputils-ping net-tools iproute2 bird2

WORKDIR /root

# Wait for netlab initial to execute bound /etc/config scripts, then start BIRD.
RUN cat >/entrypoint.sh <<'ENTRYPOINT'
#!/bin/bash
set -e

marker="${NETLAB_CONFIG_DONE:-/var/run/netlab-config-done}"
timeout="${NETLAB_CONFIG_WAIT:-120}"

while [ ! -f "$marker" ] && [ "$timeout" -gt 0 ]; do
  sleep 1
  timeout=$((timeout - 1))
done

[ -f "$marker" ] || { echo "bird: timeout waiting for ${marker}" >&2; exit 1; }

exec bird -f -c /etc/bird/bird.conf -d
ENTRYPOINT
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
