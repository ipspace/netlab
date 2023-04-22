# Integrating External Tools

Some user might want to use _netlab_ with external management tools (example: Graphite, SuzieQ, Prometheus...). It would be nice to generate the configuration files for these tools and start them as part of the **netlab up** process.

```{warning}
This proposal does not cover using multiple instances of the same tool in multilab environments. We'll open that can of worms at a later stage.
```

## Using the External Tools

Adding a tool to the lab should be as easy as adding an entry to the **tools** dictionary. For example, to start SuzieQ together with the lab, one could add:

```
tools:
  suzieq:
```

Tools should be configurable using parameters in the tool-specific dictionary. Some of these parameters are system-defined, others are defined by the tool creator. System-defined parameters include:

* **runtime** -- *docker* or *local*. A tool can be executed as a Docker container (dynamically pulled from a container repository) or as a local command (in which case the end-user is responsible for installing the prerequisite software).

## Behind the Scenes

Tools would be defined in **defaults.tools** dictionary that would specify how to:

* Create configuration files for the tool
* Start the tool during **netlab up**
* Stop the tool during **netlab down**
* Perform a cleanup during **netlab down --cleanup**

A tool dictionary could contain any number of extra parameters (as needed by the tool), and MUST contain:

* **runtime**: a list of supported runtimes. The first element in the list is the default runtime environment.
* For each supported runtime, a dictionary of start/stop commands
* **config**: a list of actions needed to create configuration files

**Notes**:
* The tool-specific configuration files will be created in per-tool directory within the current working directory.

### Configuration Actions

Tool-specific configuration files are created during the **netlab create** process using **tools** output module (which becomes another default output module to use with **netlab create**).

The **tools** output module iterates over the list of tools used by the current topology and executes tool-specific actions:

* Create configuration file from user or system (package) template
* Copy configuration file from package
* Call tool-specific output module

The actions are specified in the **config** list within tool definition. Each action contains a **dest** parameter and one of these parameters:

* **copy** -- path to the source file
* **template** -- path to the configuration file template. The template will be called in the same way as the provider templates.
* **output** -- call tool-specific output module, passing the contents of the **output** parameter to that module

### Runtime Definitions

A tool runtime definition has these entries:

* **up** (mandatory): A list of commands to execute to start the tool
* **down** (mandatory): A list of commands to execute to stop the tool
* **cleanup** (optional): A list of commands to execute during the cleanup phase (example: delete Docker volumes).
* **connect** (optional): A list of commands to execute to connect to the tool. Used by **netlab connect** command to connect to the tool.
* **message** (optional): A message to display after the tool has been started. Can be used to print out short usage instructions.

Each command is a formatted string and can use parameters from the tool definition or from the topology.

**Notes:**
* The mapping of container volumes and configuration files have to be done in the individual **up** commands.
