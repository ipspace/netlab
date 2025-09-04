(netlab-tc)=
# Control Link Impairment Parameters

The **netlab tc** command can be used to disable, enable, display, or modify [link impairment](links-netem) parameters on [*libvirt* virtual machines](libvirt-capture) or [*containerlab*-created Docker containers](lab-clab).

```{warning}
You cannot configure link impairment on point-to-point links between *‌libvirt* virtual machines that do not have **‌tc** attributes; you have to change them into Linux bridges ([more details](libvirt-capture)).
```

The **netlab tc** command has several subcommands:

* **[netlab tc disable](netlab-tc-disable)** disables traffic control on one or more interfaces
* **[netlab tc enable](netlab-tc-enable)** restores the link impairment parameters [specified in the lab topology](links-netem)
* **[netlab tc show](netlab-tc-show)** display the *netem* traffic control policies configured on the specified interfaces
* **[netlab tc set](netlab-tc-set)** replaces or modifies *netem* traffic control parameters on the specified interfaces

## Usage

```text
usage: netlab tc [-h] [-v] [-q] [--instance INSTANCE] {enable,disable,show,set} ...

Link impairment and traffic control utilities

options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose logging (add multiple flags for increased verbosity)
  -q, --quiet           Report only major errors
  --instance INSTANCE   Specify lab instance to work on

netlab clab subcommands:
  {enable,disable,show,set}

Use 'netlab tc subcommand -h' to get subcommand usage guidelines
```

(netlab-tc-disable)=
## Disable the Link Impairment

```
usage: netlab tc disable [-h] [-n NODE] [-i INTF] [--all]

Disable link impairments

options:
  -h, --help            show this help message and exit
  -n NODE, --node NODE  Disable traffic control only on selected node
  -i INTF, --interface INTF
                        Disable traffic control only on selected interface
  --all                 Disable traffic control on all lab links
```

You can use the **netlab tc disable** command to remove *netem* traffic control policy from:

* Individual interfaces (specify `--node` and `--interface` parameters)
* All interfaces of a specified node (specify only the `--node` parameter)
* All interfaces having **tc** attributes in the lab topology (omit `--node` and `--interface` parameters)
* All lab interfaces (with the `--all` flag)

(netlab-tc-enable)=
## Restore the Lab Topology Link Impairment Parameters

```
usage: netlab tc enable [-h] [-n NODE] [-i INTF]

Enable topology-defined link impairments

options:
  -h, --help            show this help message and exit
  -n NODE, --node NODE  Enable traffic control only on selected node
  -i INTF, --interface INTF
                        Enable traffic control only on selected interface
```

You can use the **netlab tc enable** command to restore the link impairment parameters specified in the lab topology on:

* Individual interfaces (specify `--node` and `--interface` parameters)
* All interfaces of a specified node (specify only the `--node` parameter)
* All interfaces having **tc** attributes in the lab topology (omit `--node` and `--interface` parameters)

(netlab-tc-show)=
## Display the Link Impairment Parameters

```
$ netlab tc show -h
usage: netlab tc show [-h] [-n NODE] [-i INTF]

Display configured traffic control

options:
  -h, --help            show this help message and exit
  -n NODE, --node NODE  Display traffic control only on selected node
  -i INTF, --interface INTF
                        Display traffic control only on selected interface
```

Use the **netlab tc show** command to display *netem* traffic control parameters configured on specified nodes, interfaces, or the whole lab (when you execute the command without `--node` or `--interface` parameter).

Example:

```
$ netlab tc show
[INFO]    Traffic control on n1 eth2: limit 1000 rate 200Kbit
[INFO]    Traffic control on n2 eth2: limit 1000 delay 300ms
```

(netlab-tc-set)=
## Set or Modify the Link Impairment Parameters

```
usage: netlab tc set [-h] [-n NODE] [-i INTF] [--corrupt CORRUPT] [--delay DELAY]
                     [--duplicate DUPLICATE] [--jitter JITTER] [--loss LOSS]
                     [--rate RATE] [--reorder REORDER] [--modify]

Set or modify traffic control parameters

options:
  -h, --help            show this help message and exit
  -n NODE, --node NODE  Change traffic control only on selected node
  -i INTF, --interface INTF
                        Change traffic control only on selected interface
  --corrupt CORRUPT     Percentage of corrupt packets
  --delay DELAY         Delay in msec
  --duplicate DUPLICATE
                        Percentage of duplicate packets
  --jitter JITTER       Jitter in msec
  --loss LOSS           Percentage of lost packets
  --rate RATE           Rate in kbps
  --reorder REORDER     Percentage of reordered packets
  --modify              Modify existing traffic control parameters
```

Use the **netlab tc set** command to set or modify *netem* traffic control parameters on specified nodes, interfaces, or all lab interfaces (when you execute the command without `--node` or `--interface` parameter).

Unless you use the `--modify` keyword, the specified parameters will overwrite the current link impairment parameters.

Example:

```
$ netlab tc show
[INFO]    Traffic control on n1 eth2: limit 1000 rate 200Kbit
[INFO]    Traffic control on n2 eth2: limit 1000 delay 300ms

$ netlab tc set --node n1 --interface eth2 --delay 10
[INFO]    Traffic control on n1 eth2: delay 10.0ms 0ms

$ netlab tc show
[INFO]    Traffic control on n1 eth2: limit 1000 delay 10ms
[INFO]    Traffic control on n2 eth2: limit 1000 delay 300ms

$ netlab tc set --node n1 --interface eth2 --rate 200 --modify
[INFO]    Traffic control on n1 eth2: rate 200000.0

$ netlab tc show
[INFO]    Traffic control on n1 eth2: limit 1000 rate 200Kbit
[INFO]    Traffic control on n2 eth2: limit 1000 delay 300ms
```
