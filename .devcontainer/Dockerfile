FROM mcr.microsoft.com/devcontainers/python:3.11-bookworm

ARG PIP_OPTIONS
ENV PIP_OPTIONS=${PIP_OPTIONS}
ENV NETLAB_DEVICES_FRR_CLAB_GROUP__VARS_NETLAB__MGMT__VRF=False
ENV ANSIBLE_CONFIG=./ansible.cfg
LABEL org.opencontainers.image.source https://github.com/ipspace/netlab

RUN echo "deb [trusted=yes] https://netdevops.fury.site/apt/ /" | \
    tee -a /etc/apt/sources.list.d/netdevops.list

# setup keyring for github cli
RUN sudo mkdir -p -m 755 /etc/apt/keyrings \
    && wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
    && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null

# install containerlab and tools
RUN apt update && \
    apt install -y python3-pip && \
    python3 -m pip install --break-system-packages $PIP_OPTIONS networklab && \
    apt install -y --no-install-recommends containerlab \
    btop \
    gh \
    iputils-ping \
    tcpdump \
    iproute2 \
    dnsutils \
    telnet \
    linux-headers-generic && \
    netlab install --yes ubuntu ansible

# add empty docker config files to avoid clab warnings for root user
RUN mkdir -p /root/.docker && echo "{}" > /root/.docker/config.json

# maintain SSH_AUTH_SOCK env var when using sudo
RUN mkdir -p /etc/sudoers.d && echo 'Defaults env_keep += "SSH_AUTH_SOCK"' > /etc/sudoers.d/ssh_auth_sock

# vscode user is created in the MS devcontainer image
USER vscode

# create ssh key for vscode user to enable passwordless ssh to devices
RUN ssh-keygen -t ecdsa -b 256 -N "" -f ~/.ssh/id_ecdsa && \
    mkdir -p /home/vscode/.docker && \
    echo "{}" > /home/vscode/.docker/config.json

# setup zsh
#COPY ./.devcontainer/zsh/.zshrc /home/vscode/.zshrc
#COPY ./.devcontainer/zsh/.p10k.zsh /home/vscode/.p10k.zsh
#COPY ./.devcontainer/zsh/install-zsh-plugins.sh /tmp/install-zsh-plugins.sh
#RUN bash -c "/tmp/install-zsh-plugins.sh"
