(extool-netlab-ui)=
# netlab-ui

[netlab-ui](https://github.com/Muddyblack/netlab-ui) is a web-based topology editor and lab manager for _netlab_. 
It displays the lab topology, lets you edit nodes, links, and module parameters, starts and stops the lab, and opens shells and log streams to lab devices in the browser. Just like the containerlab-app does but with direct support for netlab logic.

Add the following lines to a lab topology file to start netlab-ui together with the lab:

```
tools:
  netlab_ui:
```

The URL of the web interface is printed during the **netlab up** process. You can also display it with the **netlab connect netlab_ui** command.

## Parameters

You can change these tool parameters in the lab topology or in [user defaults](tools-enable-default) (**defaults.tools.netlab_ui**):

* **host** -- the IP address the web server listens on. The default (`127.0.0.1`) accepts connections only from the lab server; use an SSH tunnel (for example, `ssh -L 8000:localhost:8000 labserver`) to reach it from your workstation, or set it to `0.0.0.0` together with **auth**.
* **port** -- the TCP port of the web interface (default: `8000`). The [multilab plugin](plugin-multilab) ID is added to the port number, so you can use netlab-ui with several lab instances on the same server.
* **auth** -- `user:password`. When set, the web interface, its API, and device terminals require HTTP basic authentication.
* **image** -- the container image (default: `ghcr.io/muddyblack/netlab-ui:latest-full`). The default image includes _netlab_, Ansible, and _containerlab_.

For example, to make netlab-ui reachable from other hosts:

```
tools:
  netlab_ui:
    host: 0.0.0.0
    auth: admin:changeme
```

## Notes

* netlab-ui manages the lab in the directory in which you executed **netlab up**. The container runs with the same privileges as _containerlab_ (privileged mode, host network, and host PID namespace) and has access to the Docker socket, the lab directory, and the `~/.netlab` directory in which _netlab_ tracks running labs.
* The container is removed when you shut down the lab with **netlab down**. When you stop or restart the lab from the netlab-ui web interface, the tool keeps running.
* netlab-ui can also run without a lab topology, as a standalone container or a Python/Node application. See the [netlab-ui quick start](https://github.com/Muddyblack/netlab-ui#quick-start) for details.
