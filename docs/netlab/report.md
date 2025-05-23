(netlab-report)=
# Creating a Report

The **netlab report** command creates a report from the transformed lab topology data (usually stored in `netlab.snapshot.yml`) created by the **netlab create** command. It replicates the functionality of the **netlab create -o report:_name_** command with a more convenient user interface.

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

## Examples

* `netlab report addressing` creates lab addressing report in text format on standard output (printed to the screen)
* `netlab report addressing.html x.html` creates an HTML addressing report (**addressing.html**) and stores it into `x.html`.
* `netlab report bgp-neighbor.md` creates the table of BGP neighbors in Markdown format
* `netlab report bgp-neighbor.ascii` creates the Markdown BGP neighbors report and renders it as ASCII text using the [rich.markdown](https://rich.readthedocs.io/en/stable/markdown.html) library.
* `netlab report addressing --node r1,r2` creates addressing report for R1 and R2.

```{tip}
[**netlab inspect** documentation](netlab-inspect-node) describes how to specify the nodes on which the command will be executed.
```
