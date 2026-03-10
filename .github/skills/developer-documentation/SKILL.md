---
name: developer-documentation
description: Write configuration template developer documentation
---
# Documentation Guidelines

* The documentation files must be in `docs/dev/config`
* The new files have to be included in ToC in `docs/dev/config/index.md`
* The *configuration template developer* documentation is not the user guide. The data structures described must match the output of the transformation process, not the input attribute schema, and there are significant differences between the two.
* There is no need to include supported platforms or more than three sample templates.
* The documentation must describe all relevant **node** attributes, followed by all relevant **interface** attributes. When needed, add VLAN- or VRF attributes.
* Do not explain the lab topology attributes; they have their own documentation.
* Find the relevant tests in the `tests/integration` directory tree and mention them
* Do not use `jinja2` syntax highlighter; it does not work.
* Mention where the configuration templates should be stored, and how the platform name is calculated (based on `netlab_device_type` or `ansible_network_os` variable)
