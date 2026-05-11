# Restart a Virtual Lab Instance

Use the **netlab restart** command to shut down and restart a running lab instance. You can use this command if the lab is messed up beyond hope, or after changing the lab topology file.

This command executes **[netlab down](down.md)** followed by **[netlab up](up.md)** to restart your lab from the lab topology from which the lab snapshot file (usually `netlab.snapshot.pickle`) was created. The commands are executed in the current directory unless you specify a different lab instance with the `--instance` parameter.

```{warning}
* **netlab restart** does not support the extra parameters that can be used with **netlab create** or **netlab up** to adjust the lab topology. If you want to change lab topology settings with CLI parameters, use the **netlab down** and **netlab up** commands.
```

## Usage

```text
usage: netlab restart [-h] [--log] [-v] [-q] [--no-config] [--fast-config] [-i INSTANCE]
                      [--snapshot [SNAPSHOT]]

Reconfigure and restart the virtual lab

options:
  -h, --help            show this help message and exit
  --log                 Enable basic logging
  -v, --verbose         Verbose logging (add multiple flags for increased verbosity)
  -q, --quiet           Report only major errors
  --no-config           Do not configure lab devices
  --fast-config         Use fast device configuration (Ansible strategy = free)
  -i, --instance INSTANCE
                        Specify the lab instance to restart
  --snapshot [SNAPSHOT]
                        Transformed topology snapshot file
```

Notes:

* **netlab restart** gets the original lab topology name from the `netlab.snapshot.pickle` file created by **netlab up** or **netlab create**. You could (but probably should not) specify a different snapshot file with the `--snapshot` parameter.
* With the `--instance` flag, you can shut down a lab instance running in a different directory. Use the `netlab status --all` command to display all running instances.
