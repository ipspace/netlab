# Integrating External Tools

Some user might want to use _netlab_ with external management tools (example: Graphite, SuzieQ, Prometheus...). _netlab_ can automatically generate the configuration files for these tools and start them as the last step in the **netlab up** process (after the lab has been configured).

The external tools started with _netlab_ can access the management network and the management interfaces of lab devices. If you need access to lab links start your tool as a [Linux container with a custom image](labs/clab.md#deploying-linux-containers).

```{warning}
* Tools are started as Docker containers. You have to run your labs on a Linux server with Docker to use external tools with _netlab_.[^DI]
* When using containers as lab devices _netlab_ connects tool containers to the lab management network and they get IPv4 addresses from the beginning of the management IPv4 prefix. Do not change [**addressing.mgmt.start** parameter](addressing.md) to a very low value when using external tools.
```

[^DI]: You can use **netlab install containerlab** to install Docker on a Ubuntu server.

## Using the External Tools

Adding a tool to the lab is as easy as adding an entry to the **tools** dictionary. For example, to start SuzieQ together with the lab, simple add the following two lines to the lab topology file:

```
tools:
  suzieq:
```

You can configure individual tools using parameters in the tool-specific dictionary. Some of these parameters are system-defined, others are defined by the tool creator. System-defined parameters include:

* **runtime** -- execution environment. The only supported value is *docker* (Docker container dynamically pulled from a container repository). If you want to start the tools on the Linux host, define *local* execution environment ([details](dev/extools.md)).

For the list of tool-specific parameters see the individual tool description.

(extools-list)=
## Supported Tools

_netlab_ includes definitions for the following tools:

```eval_rst
.. toctree::
   :maxdepth: 1

   extool/graphite.md
   extool/suzieq.md
```

It's relatively easy to add your own tools to the **defaults.tools** dictionary. Read [](dev/extools.md) for more details.
