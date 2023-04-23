# Integrating External Tools

Some user might want to use _netlab_ with external management tools (example: Graphite, SuzieQ, Prometheus...). _netlab_ can automatically generate the configuration files for these tools and start them as the last step in the **netlab up** process (after the lab has been configured).

The external tools started with _netlab_ can access the management network and the management interfaces of lab devices. If you need access to lab links start your tool as a [Linux container with a custom image](labs/clab.md#deploying-linux-containers).

```eval_rst
.. contents:: Table of Contents
   :local:
```

```{warning}
This is an experimental functionality with the following limitations:

* Tools are started as Docker containers. You have to run your labs on a Linux server with Docker; you can use **‌netlab install containerlab** to install Docker.
* You can use external tools with *‌libvirt* provider, but not with *‌containerlab* or multi-provider topologies due to the way Docker isolates container bridges. This limitation will be fixed in a future release.
```

## Using the External Tools

Adding a tool to the lab is as easy as adding an entry to the **tools** dictionary. For example, to start SuzieQ together with the lab, simple add the following two lines to the lab topology file:

```
tools:
  suzieq:
```

You can configure individual tools using parameters in the tool-specific dictionary. Some of these parameters are system-defined, others are defined by the tool creator. System-defined parameters include:

* **runtime** -- execution environment. The only supported value is *docker* (Docker container dynamically pulled from a container repository). If you want to start the tools on the Linux host, define *local* execution environment ([details](dev/extools.md).

For the list of tool-specific parameters see the [descriptions of individual tools](extools-list).

(extools-list)=
## Supported Tools

_netlab_ includes definitions for the following tools:

* [](extools-suzieq)

It's relatively easy to add your own tools to the **defaults.tools** dictionary. Read [](dev/extools.md) for more details.

(extools-suzieq)=
### SuzieQ

SuzieQ is the first open source, multi-vendor network observability platform application.

* Add the following lines to the lab topology file to use SuzieQ with _netlab_:

```
tools:
  suzieq:
```

* Use **netlab connect suzieq** command to start the SuzieQ CLI.
* SuzieQ tool has no configurable parameters

**Notes:**

* SuzieQ GUI is not yet supported
* Data collected by SuzieQ is deleted when the lab is shut down.
