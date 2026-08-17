(build-dnsmasq)=
# Building dnsmasq Containers

The _netlab_ dnsmasq container includes the dnsmasq DNS/DHCP server and the rsyslog Syslog server. You must build a local container image with the **[netlab clab build dnsmasq](netlab-clab-build)** command before you can use `device: dnsmasq` (which only works with `provider: clab`).

The *dnsmasq* server starts when the container provides DNS or DHCP services, and the *rsyslog* server starts when the container provides Syslog services.

The default *dnsmasq* device settings enable DHCP, DNS, and syslog servers.
