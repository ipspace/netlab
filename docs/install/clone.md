# Installing *netlab* from GitHub

If you want to change *netlab* source code, need the latest development version, or want to contribute to the project, clone the *netlab* GitHub repository. Everyone else should [install the Python package](package).

* Clone the [netlab Github repository](https://github.com/ipspace/netlab) with `git clone https://github.com/ipspace/netlab`.
* Switch to the development branch with `git checkout dev`, or select the desired release with `git checkout release_*`. Use `git tag` to get the list of release tags.
* Within the **netlab** directory, install prerequisite Python packages with `python3 -m pip install -r requirements.txt`.
* If you want to contribute to the project, install additional Python packages with `python3 -m pip install -r requirements-dev.txt`.
* Install Ansible or use [ipSpace network automation container image](https://hub.docker.com/r/ipspace/automation). 
* Add **netlab** directory to your PATH with `source setup.sh` command executed within **netlab** directory.

Next step: [create the lab environment](lab)
