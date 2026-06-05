# Installing *netlab* from GitHub

If you want to change *netlab* source code, need the latest development version, or want to contribute to the project, clone the *netlab* GitHub repository. Everyone else should [install the Python package](package).

* Clone the [netlab Github repository](https://github.com/ipspace/netlab) with `git clone https://github.com/ipspace/netlab`.
* Switch to the development branch with `git checkout dev`, or select the desired release with `git checkout release_*`. Use `git tag` to get the list of release tags.
* Within the **netlab** directory, install prerequisite Python packages with `python3 -m pip install -r requirements.txt`.
* If you want to contribute to the project, install additional Python packages with `python3 -m pip install -r requirements-dev.txt`.
* Install Ansible or use [ipSpace network automation container image](https://hub.docker.com/r/ipspace/automation). 
* Add **netlab** directory to your PATH with `source setup.sh` command executed within **netlab** directory. Alternatively, you could install the `networklab` package from the local source (and create the `netlab` command in the `~/.local/bin` directory) with the `pip3 install -e .` command[^NST].

Next step: [create the lab environment](lab)

[^NST]: This command will break on Ubuntu 22.04 unless you upgrade **pip** and **setuptools** packages with `pip3 install --upgrade pip setuptools`. You will have to add the `--break-system-packages` flag when running **pip3** on newer Ubuntu versions unless you created a Python virtual environment.
