# Creating a Report

**netlab report** command creates a report from the transformed lab topology data (usually stored in `netlab.snapshot.yml`) created by **netlab create** command. It's replicating the functionality of **netlab create -o report:_name_** command with a more convenient user interface.

## Usage

```text
usage: netlab report [-h] [--snapshot [SNAPSHOT]] report [output]

Create a report from the transformed lab topology data

positional arguments:
  report                Name of the report you want to create
  output                Output file name (default: stdout)

options:
  -h, --help            show this help message and exit
  --snapshot [SNAPSHOT]
                        Transformed topology snapshot file
```

## Examples

* **netlab report addressing** creates lab addressing report in text format on standard output (printed to the screen)
* **netlab report addressing.html x.html** creates HTML addressing report (**addressing.html**) and stores it into `x.html`.
