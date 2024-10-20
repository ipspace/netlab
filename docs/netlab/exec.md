(netlab-exec)=
# Executing Commands on Lab Devices

**netlab exec** command uses information stored in the _netlab_ snapshot file and reported with the **[`netlab inspect --node`](inspect.md)** command to execute a command on one or more lab devices using SSH or **docker exec**.

## Usage

```text
usage: netlab exec [-h] [-v] [-q] [--dry-run] [--snapshot [SNAPSHOT]]                      
                      node

Executes a command on one or more network devices

positional arguments:
  node                  Device(s) to execute the command on

options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose logging
  -q, --quiet           No logging
  --dry-run             Print the commands that would be executed, but do not execute them
  --snapshot [SNAPSHOT]
                        Transformed topology snapshot file

The rest of the arguments are passed to SSH or docker exec command
```

```{warning}
Do not use **netlab exec** in a production environment.
```
