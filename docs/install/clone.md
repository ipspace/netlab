# Installing *netsim-tools* from GitHub

If you want to change *netsim-tools* source code, need the latest development version, or want to contribute to the project, clone the *netsim-tools* GitHub repository. Everyone else should [install the Python package](../install.md#installing-netsim-tools).

* Clone the [netsim-tools Github repository](https://github.com/ipspace/netsim-tools) with `git clone https://github.com/ipspace/netsim-tools`.
* Switch to the development branch with `git checkout dev`, or select the desired release with `git checkout release_*`. Use `git tag` to get the list of release tags.
* Within the **netsim-tools** directory, install prerequisite Python packages with `python3 -m pip install -r requirements.txt`.
* If you want to contribute to the project, install additional Python packages with `python3 -m pip install -r requirements-dev.txt`.
* Install Ansible or use [ipSpace network automation container image](https://hub.docker.com/r/ipspace/automation). 
* Add **netsim-tools** directory to your PATH with `source setup.sh` command executed within **netsim-tools** directory.

Next step: [create the lab environment](../install.md#creating-a-lab-environment)
