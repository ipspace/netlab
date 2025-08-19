(netlab-usage)=
# Display Usage Statistics

**netlab** collects local usage statistics in the `~/.netlab/stats.json` file. You can view the contents of that file with any program capable of displaying JSON data (**jq** is a nice option), and display some statistics with the **netlab usage show** command.

You can also start or stop the collection of usage statistics or clear them.

```text
Usage:

    netlab usage <action> <parameters>

The 'netlab usage' command can execute the following actions:

 start   (re)start collecting local usage statistics
 stop    stop collecting usage statistics
 clear   clear collected usage statistics
 show    display collected usage statistics

Use 'netlab usage <action> --help' to get action-specific help
```

The **netlab usage show** command can display these statistics:

* **commands** -- the netlab commands you're using
* **devices** -- the devices and virtualization providers used in your lab topologies
* **modules** -- the modules used in your lab topologies
* **plugins** -- the plugins used in your lab topologies
