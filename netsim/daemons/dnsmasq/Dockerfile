FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

LABEL maintainer="Netlab project <netlab.tools>"
LABEL description="dnsmasq DHCP/DNS server"

RUN set -eux; \
    apt-get update; \
    apt-get install -y iputils-ping net-tools dnsmasq rsyslog; \
    cat <<'SCRIPT' >/etc/netlab-start.sh
#!/bin/bash
/usr/sbin/dnsmasq -R -C /etc/dnsmasq.conf --no-daemon &
wait
echo "Exiting"
SCRIPT

WORKDIR /root

CMD [ "/bin/sh","/etc/netlab-start.sh" ]
