(install-clone)=
# Installing *netlab* from GitHub

If you want to change the *netlab* source code, need the latest development version, or want to contribute to the project, clone the *netlab* GitHub repository (everyone else should [install the Python package](install-linux-netlab)).

* Clone the [netlab Github repository](https://github.com/ipspace/netlab) with `git clone https://github.com/ipspace/netlab`.
* Switch to the development branch with `git checkout dev`, or select the desired release with `git checkout release_*`. Use `git tag` to get the list of release tags.
* Within the **netlab** directory, install prerequisite Python packages with `python3 -m pip install -r requirements.txt`[^BSP].
* If you want to contribute to the project, install additional Python packages with `python3 -m pip install -r requirements-dev.txt`.
* Add the **netlab** directory to your PATH with `source setup.sh` command executed within the **netlab** directory. Alternatively, you could install the `networklab` package from the local source (and create the `netlab` command in the `~/.local/bin` directory) with the `pip3 install -e .` command[^NST].
* (Optional) Use the **[netlab install](netlab-install)** command to install Ubuntu utilities, containerlab, libvirt/KVM, or Ansible.

Next step: [create the lab environment](lab)

[^NST]: This command will break on Ubuntu 22.04 unless you upgrade **pip** and **setuptools** packages with `pip3 install --upgrade pip setuptools`.

[^BSP]: You will have to use a Python virtual environment or add the `--break-system-packages` flag when running **pip3** on recent Linux distributions.
