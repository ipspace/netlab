FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

LABEL maintainer="Netlab project <netlab.tools>"
LABEL description="VirtualBMC - IPMI emulation for libvirt"

RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-libvirt \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install virtualbmc --break-system-packages

# Create VirtualBMC configuration directory
RUN mkdir -p /root/.vbmc

WORKDIR /root

# VirtualBMC daemon needs to run in foreground mode for containers
CMD [ "vbmcd", "--foreground" ]