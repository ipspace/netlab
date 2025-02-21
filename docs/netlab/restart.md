# Restart Virtual Lab

**netlab restart** executes **[netlab down](down.md)** followed by **[netlab up](up.md)** to restart your lab from the transformed lab topology stored in `netlab.snapshot.yml` snapshot file.

You can use **netlab restart** to restart the existing lab (use `--snapshot` keyword) or recreate the lab configuration files if you changed the lab topology.

```{warning}
* **netlab restart** does not support `-d`, `-p` or `-s` flags used by **netlab create** or **netlab up**. If you want to change lab topology settings with CLI parameters, use **netlab down** and **netlab up** commands.
* You must execute the **‌netlab restart** command within the lab directory.
```

## Usage

```text
$ netlab restart -h
usage: netlab [-h] [--log] [-v] [-q] [--no-config] [--fast-config]
              [--snapshot [SNAPSHOT]]
              [topology]

Reconfigure and restart the virtual lab

positional arguments:
  topology              Topology file (default: topology.yml)

options:
  -h, --help            show this help message and exit
  --log                 Enable basic logging
  -v, --verbose         Verbose logging (add multiple flags for increased verbosity)
  -q, --quiet           Report only major errors
  --no-config           Do not configure lab devices
  --fast-config         Use fast device configuration (Ansible strategy = free)
  --snapshot [SNAPSHOT]
                        Transformed topology snapshot file
```
