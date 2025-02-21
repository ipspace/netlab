(netlab-exec)=
# Executing Commands on Lab Devices

**netlab exec** command uses information stored in the _netlab_ snapshot file and reported with the **[`netlab inspect --node`](inspect.md)** command to execute a command on one or more lab devices using SSH or **docker exec**.

## Usage

```text
$ netlab exec -h
usage: netlab exec [-h] [-v] [-q] [--dry-run] [-i INSTANCE] node

Run a command on one or more network devices

positional arguments:
  node                  Node(s) to run command on

options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose logging (add multiple flags for increased verbosity)
  -q, --quiet           Report only major errors
  --dry-run             Print the hosts and the commands that would be executed on them,
                        but do not execute them
  -i INSTANCE, --instance INSTANCE
                        Specify lab instance to execute commands in

The rest of the arguments are passed to SSH or docker exec command
```

```{warning}
Do not use **netlab exec** in a production environment.
```
