# Emulating Legacy CLI Commands

Earlier releases of *netsim-tools* used numerous Bash scripts and Ansible playbooks that are now included in the Python **netsim-tools** package. To use those tools directly, download the source code from the [GitHub repository](https://github.com/ipspace/netsim-tools) and use `source setup.sh` to set up the PATH variable; to emulate them with **netlab** commands, set up Bash aliases with **netlab alias**.

## Usage

```
$ eval "$(netlab alias)"
```

The following aliases are create by the **netlab alias** command:

```
$ netlab alias
#
# Aliases for old netsim-tools CLI commands
#
alias connect.sh="netlab connect"
alias initial-config.ansible="netlab initial"
alias create-config.ansible="netlab initial -o config"
alias collect-configs.ansible="netlab collect -o config"
alias config.ansible="netlab config -"
alias create-topology="netlab topology"
```
