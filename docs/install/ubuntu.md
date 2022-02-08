# Ubuntu Server Installation

If you want to install *netsim-tools* and all its dependencies on an existing Ubuntu server (bare-metal or VM):

* If needed, install Python3 and **pip3** with `sudo apt-get update && sudo apt-get install -y python3-pip`
* Install *netsim-tools* package with `sudo python3 -m pip install netsim-tools` or your preferred Python package installation procedure.
* Install additional software with `sudo netlab install ubuntu ansible libvirt containerlab` command ([more details](../netlab/install.md)) or follow [generic Linux installation instructions](linux.md).

```eval_rst
.. toctree::
   :caption: Next Steps
   :maxdepth: 1
   :titlesonly:

   ../labs/libvirt.md
   ../labs/clab.md
```
