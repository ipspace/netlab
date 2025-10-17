FROM quay.io/netscaler/netscaler-cpx:13.1-60.29

ENV EULA=yes

# Build arguments for clab user credentials
ARG CLAB_USER=clab
ARG CLAB_PASSWORD=clab@123
ENV CLAB_USER=${CLAB_USER}
ENV CLAB_PASSWORD=${CLAB_PASSWORD}

# Create user on the system for SSH access
RUN useradd -m ${CLAB_USER} && echo "${CLAB_USER}:${CLAB_PASSWORD}" | chpasswd

# Create required directories and permissions
RUN mkdir -p /var/nstmp && \
    chmod 777 /var/nstmp

# Provision script - give clab user superuser privileges
RUN (echo '#!/bin/bash'; \
     echo "cli_script.sh \"add system user ${CLAB_USER} ${CLAB_PASSWORD} -promptString '%u@%h'\""; \
     echo "cli_script.sh \"bind system user ${CLAB_USER} superuser 0\""; \
     echo 'cli_script.sh "save ns config"') > /provision.sh && \
    chmod +x /provision.sh

# nscli wrapper - allows clab user to enter nscli, already logged in
RUN (echo '#!/bin/bash'; \
     echo "exec nscli -U 127.0.0.1:${CLAB_USER}:${CLAB_PASSWORD}") > /usr/local/bin/nscli-wrapper && \
    chmod +x /usr/local/bin/nscli-wrapper

# Set nscli wrapper as default shell for user
RUN usermod -s /usr/local/bin/nscli-wrapper ${CLAB_USER}

# Entrypoint - runs startup and also provisioning if container is not already initialized
# the timing of 120 seconds is required to ensure the netscaler is fully started before creating the user
# when tested with 14.1, 120 was no longer enough, it might need to be increased to 180 seconds for future versions
RUN (echo '#!/bin/bash'; \
     echo 'if [ ! -f /initialized ]; then'; \
     echo '  /var/netscaler/bins/docker_startup.sh &'; \
     echo '  sleep 120'; \
     echo '  /provision.sh'; \
     echo '  touch /initialized'; \
     echo 'else'; \
     echo '  /var/netscaler/bins/docker_startup.sh'; \
     echo 'fi'; \
     echo 'wait') > /entrypoint.sh && \
    chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
EXPOSE 22 9080 9443
