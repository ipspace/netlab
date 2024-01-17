FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

LABEL maintainer="Netlab project <netlab.tools>"
LABEL description="BIRD Internet Routing Daemon (bird.network.cz)"

RUN mkdir /etc/bird && mkdir /run/bird && apt-get update && apt-get install -y iputils-ping net-tools bird

WORKDIR /root

CMD bird -c /etc/bird/bird.conf -d
