(extool-nuts)=
# Network Unit Testing System (NUTS)

NUTS is a Pytest plugin enabling network testing using YAML files.

* Add the following lines to the lab topology file to use NUTS with _netlab_:

```
tools:
  nuts:
```

* Use the **netlab connect nuts** command to run pytest or **netlab connect nuts bash** to open a shell in the docker container.

**Notes:**

* All necessary files are created in the folder nuts and mounted to the docker container.
