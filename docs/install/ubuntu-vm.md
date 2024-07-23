# Ubuntu VM Installation

Suppose you'd like to use *netlab* with *libvirt*[^1] or run network devices as containers on a Windows- or MacOS-based computer. You'll have to run the whole toolchain needed to create networking labs (netlab ⇨ Vagrant ⇨ libvirt ⇨ KVM) within a Linux virtual machine.

The easiest way to set up your lab environment is to create a Ubuntu virtual machine and use the **netlab install** command within that virtual machine to install the required software packages[^2]. You could also run _netlab_ on a [Ubuntu instance in a public cloud](cloud.md).

![Running Ubuntu VM on a desktop OS](ubuntu-on-desktop-os.png)

[^1]: The *libvirt* Vagrant plugin starts all network devices in parallel, resulting in a much faster lab setup than Vagrant with Virtualbox.

[^2]: See also the [tutorial created by Leo Kirchner](https://blog.kirchne.red/posts/netsim-tools-quickstart/).

```{warning}
Running *‌libvirt* within an Ubuntu VM requires *‌nested virtualization*. You don't need nested virtualization to run Docker containers within a Ubuntu VM.

Nested virtualization was available in VMware Workstation/Fusion for years and was recently added to VirtualBox. While VMware products perform flawlessly, we experienced unacceptable performance with VirtualBox nested virtualization on some Intel CPUs.
```

[Canonical Multipass](https://multipass.run/) is probably the easiest way to start a Ubuntu VM on your laptop if you don't need nested virtualization. Create an instance with [as much RAM and as many CPU cores](https://multipass.run/docs/create-an-instance#heading--create-an-instance-with-custom-cpu-number-disk-and-ram) as you can afford, and [install the necessary software on it](ubuntu-vm-manual).

You can also use [Vagrant](ubuntu-vm-vagrant) or [create the virtual machine yourself](ubuntu-vm-manual) (using, for example, VirtualBox or VMware GUI)

(ubuntu-vm-vagrant)=
## Creating Ubuntu VM with Vagrant

You can use Vagrant on your computer to set up an Ubuntu VM. Vagrant will automatically:

* Download the required virtual disk image
* Start the virtual machine
* Enable SSH access to the virtual machine
* Provision the software on the virtual machine

Installation steps:

* Install [VirtualBox](https://www.virtualbox.org/wiki/Downloads) or VMware Fusion/Workstation
* Install [Vagrant](https://www.vagrantup.com/docs/installation)
* Install [Vagrant VMware provider](https://www.vagrantup.com/docs/providers/vmware) if you're using VMware Workstation/Fusion.
* Create an empty directory. In that directory, create a **Vagrantfile** with the following content. Change the **memory**/**memsize** or **cpus**/**numvcpus** settings to fit your hardware.

```
Vagrant.configure("2") do |config|
  config.vm.box = "generic/ubuntu2204"

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "8192"
    vb.cpus = 4
    vb.customize ['modifyvm', :id, '--nested-hw-virt', 'on']
  end

  config.vm.provider "vmware_fusion" do |v|
    v.vmx["memsize"] = 8192
    v.vmx["numvcpus"] = "4"
    v.vmx["vhv.enable"] = "TRUE"
  end

  config.vm.provider "vmware_desktop" do |v|
    v.vmx["memsize"] = 8192
    v.vmx["numvcpus"] = "4"
    v.vmx["vhv.enable"] = "TRUE"
  end

  config.vm.provision "shell", privileged: false, inline: <<-SHELL
    sudo apt-get update
    sudo apt-get install -y python3-pip
    sudo pip3 install --ignore-installed networklab
    sudo pip3 install --upgrade pyopenssl cryptography
    netlab install -y ubuntu ansible libvirt containerlab
  SHELL
end
```

```{tip}
The above Vagrantfile installs Python packages as root. That differs from the recommended best practice and is used primarily because we're setting up a single-purpose VM.
```

* Execute **vagrant up** and wait for the installation to complete. If you're using VMware Workstation or Fusion, specify the **--provider** argument in the **vagrant up** command when creating the VM (but not on subsequent starts).
* Log into the virtual machine with **vagrant ssh** and test the installation with **netlab test**

(ubuntu-vm-manual)=
## Manual Virtual Machine Provisioning

* Create an Ubuntu 22.04 or Ubuntu 24.04 virtual machine within your virtualization environment (you'll find plenty of online tutorials). If needed, enable nested virtualization.
* Log into the virtual machine
* Execute these commands to download Python3 and install *netlab*, Ansible, vagrant, libvirt, KVM, containerlab, and Docker.

```
sudo apt-get update
sudo apt-get install -y python3-pip
sudo pip3 install --ignore-installed networklab
sudo pip3 install --upgrade pyopenssl cryptography
netlab install -y ubuntu ansible libvirt containerlab
```

```{tip}
* Installing Python packages as root is not the recommended best practice. We're using this approach because we're setting up a single-purpose VM.
* Ubuntu 22.04 wants you to install Python packages in a virtual environment. To stop the complaints, add the `--break-system-packages` option to the **pip3 install** command.
```

* After completing the software installation, log out from the VM, log back in, and test your installation with the **[netlab test](netlab-test)** command. If those tests fail, you might have to use **usermod** to add your user to the *libvirt* and *docker* groups.

```eval_rst
.. toctree::
   :caption: Next Steps
   :maxdepth: 1
   :titlesonly:

   ../labs/libvirt.md
   ../labs/clab.md
```
