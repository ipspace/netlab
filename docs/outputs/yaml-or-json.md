# YAML and JSON Output Modules

*yaml* and *json* output modules display transformed lab topology in YAML or JSON format. You can invoke them by specifying `-o yaml` or `-o json` parameter in **netlab create** command.

Both output modules can take an optional destination file name (default: stdout).

Multiple formatting modifiers (separated with colons) can be used to reduce the amount of information in transformed lab topology:

* **nodefault** -- Remove default settings (**defaults** key).
* **noaddr** -- Remove address pools (**addressing** key).
* **nodes** -- Display the list of nodes.
* **links** -- Display the list of links.
