(extool-suzieq)=
# SuzieQ

SuzieQ is the first open-source, multi-vendor network observability platform.

* Add the following lines to the lab topology file to use SuzieQ with _netlab_:

```
tools:
  suzieq:
```

* Use the **netlab connect suzieq** command to start the interactive SuzieQ CLI or **netlab connect suzieq _command_** to execute a single command with the SuzieQ CLI.
* The SuzieQ tool has no configurable parameters

**Notes:**

* Data collected by SuzieQ is stored on a lab-specific Docker volume and remains intact across lab runs until you execute the **netlab down --cleanup** command.
* SuzieQ GUI is not yet supported
* SuzieQ supports a subset of _netlab_-supported platforms. _netlab_ does not check whether SuzieQ supports all the devices used in the lab topology.
