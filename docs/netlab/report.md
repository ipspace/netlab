(netlab-report)=
# Creating a Report

The **netlab report** command creates a report from the transformed lab topology data (usually stored in `netlab.snapshot.pickle`) created by the **netlab create** or **netlab up** command. It replicates the functionality of the **netlab create -o report:*name*** command with a more convenient user interface.

## Usage

```text
$ netlab report -h
usage: netlab report [-h] [--node NODE] [-i INSTANCE] [--snapshot [SNAPSHOT]]
                     report [output]

Create a report from the transformed lab topology data

positional arguments:
  report                Name of the report you want to create
  output                Output file name (default: stdout)

options:
  -h, --help            show this help message and exit
  --node NODE           Limit the report to selected node(s)
  -i INSTANCE, --instance INSTANCE
                        Specify lab instance to report on
  --snapshot [SNAPSHOT]
                        Transformed topology snapshot file
```

```{tip}
The **[netlab show reports](netlab-show-reports)** command displays up-to-date list of available system reports
```

(netlab-report-examples)=
## Examples

* `netlab report addressing` creates the lab addressing report in text format on standard output (printed to the screen)
* `netlab report addressing.html x.html` creates an HTML addressing report (**addressing.html**) and stores it into `x.html`.
* `netlab report bgp-neighbor.md` creates the table of BGP neighbors in Markdown format
* `netlab report bgp-neighbor.ascii` creates the Markdown BGP neighbors report and renders it as ASCII text using the [rich.markdown](https://rich.readthedocs.io/en/stable/markdown.html) library.
* `netlab report addressing --node r1,r2` creates addressing report for R1 and R2.
* `netlab report nodes` lists the space-separated node names (you can use the `--node` argument to select a subset of nodes) in a format that can be used in a **bash** script. For example, the following script (when started within a **screen** session) connects to all specified devices in separate **screen** windows[^BM]:

```
#!/bin/bash
for n in $(netlab report --node "${1:-*}" nodes); do
  echo "Connecting to $n"
  screen -t "$n" netlab connect $n &
done
```

[^BM]: The **bash** magic used for the `--node` parameter uses the value of the first script parameter or '*' if the script has no parameters. The double quotes around that magic prevent **bash** filename expansion.

```{tip}
[**netlab inspect** documentation](netlab-inspect-node) describes how to specify the nodes on which the command will be executed.
```

## Custom Reports

_netlab_ allows you to create custom reports. Store the Jinja2 template that will generate the report in the **reports** subdirectory of the current directory, user _netlab_ directory (`~/.netlab`), or system _netlab_ directory (`/etc/netlab`).

The reports that create Markdown text should include `.md` in the file name (for example, `vlans.md.j2`); those that create HTML should include `.html` in the file name.

```{warning}
The custom reports can use only built-in Jinja2 filters and a subset of Ansible's **‌ipaddr** and **‌hwaddr** filter functionality (for example, selecting components from an IP prefix).
```


