(netlab-report)=
# Creating a Report

The **netlab report** command creates a report from the transformed lab topology data (usually stored in `netlab.snapshot.yml`) created by the **netlab create** command. It replicates the functionality of the **netlab create -o report:_name_** command with a more convenient user interface.

## Usage

```text
usage: netlab report [-h] [--snapshot [SNAPSHOT]] [--node NODE] report [output]

Create a report from the transformed lab topology data

positional arguments:
  report                Name of the report you want to create
  output                Output file name (default: stdout)

options:
  -h, --help            show this help message and exit
  --snapshot [SNAPSHOT]
                        Transformed topology snapshot file
  --node NODE           Limit the report to selected node(s)
```

```{tip}
The **[netlab show reports](netlab-show-reports)** command displays up-to-date list of available system reports
```

## Examples

* `netlab report addressing` creates lab addressing report in text format on standard output (printed to the screen)
* `netlab report addressing.html x.html` creates an HTML addressing report (**addressing.html**) and stores it into `x.html`.
* `netlab report addressing --node r1,r2` creates addressing report for R1 and R2.
