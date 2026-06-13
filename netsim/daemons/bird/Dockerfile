FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

LABEL maintainer="Netlab project <netlab.tools>"
LABEL description="BIRD Internet Routing Daemon (bird.network.cz)"

RUN mkdir /etc/bird && mkdir /run/bird && apt-get update && apt-get install -y iputils-ping net-tools iproute2 bird2

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /root

ENTRYPOINT ["/entrypoint.sh"]
