FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

LABEL maintainer="Netlab project <netlab.tools>"
LABEL description="dnsmasq DHCP server"

RUN apt-get update && apt-get install -y iputils-ping net-tools dnsmasq

WORKDIR /root

CMD [ "/usr/sbin/dnsmasq", "-R", "-C", "/etc/dnsmasq.conf", "--no-daemon" ]
