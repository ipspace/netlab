# Advanced External Tools Scenarios

The basic functionality of external tools has been implemented, but it's very rudimentary. Future enhancements include:

* Support for **local** execution environment and Python virtual environments (potentially with **env**) variables
* Support for **containerlab** and multi-provider deployments
* Multiple instances of the same tool (multilab deployments)

Additional configuration file (**config** list) functionality might include:

* **copy** -- copy source file to configuration file (or we could decide that everything is a template)
* **output** -- call tool-specific output module, passing the contents of the **output** parameter to that module

Additional runtime functionality might include:

* **message**: A message to display after the tool has been started. Can be used to print out short usage instructions.
* **venv**: Python virtual environment to use in *local* runtime.
* **env**: Environment variables to use when executing runtime commands.
