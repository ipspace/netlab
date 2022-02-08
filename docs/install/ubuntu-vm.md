# Ubuntu VM Installation

If you have a Windows- or MacOS-based computer and would like to use *netsim-tools* with *libvirt*[^1] or run network devices as containers, create a Ubuntu virtual machine and run your networking lab within that virtual machine[^2].

[^1]: The *libvirt* Vagrant plugin starts all network devices in parallel, resulting in much faster lab setup than using Vagrant with Virtualbox.

[^2]: See also the [tutorial created by Leo Kirchner](https://blog.kirchne.red/netsim-tools-quickstart.html).

```{warning}
Running *‌libvirt* within a Ubuntu VM requires *‌nested virtualization*. Nested virtualization was available in VMware Workstation/Fusion for years and was recently added to VirtualBox. While VMware products perform flawlessly, you might get unacceptable performance with VirtualBox nested virtualization on some Intel CPUs (example: MacBook Pro 2020, Intel Core i5 CPU).
```

Installation steps:

* Install [VirtualBox](https://www.virtualbox.org/wiki/Downloads) or VMware Fusion/Workstation
* Install [Vagrant](https://www.vagrantup.com/docs/installation)
* Install [Vagrant VMware provider](https://www.vagrantup.com/docs/providers/vmware) if you're using VMware Workstation/Fusion.
* Create an empty directory. Create **Vagrantfile** with the following content in that directory. Change the **memory**/**memsize** or **cpus**/**numvcpus** settings to fit your hardware.

```
Vagrant.configure("2") do |config|
#  config.vm.box = "ubuntu/focal64"
  config.vm.box = "bento/ubuntu-20.04"

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

  config.vm.provision "shell", inline: <<-SHELL
    apt-get update
    apt-get install -y python3-pip
    pip3 install --ignore-installed netsim-tools
    netlab install -y ubuntu ansible libvirt containerlab
    usermod -aG libvirt vagrant
  SHELL
end
```

* Execute **vagrant up** and wait for the installation to complete.
* Log into the virtual machine with **vagrant ssh** and test the installation with **netlab test**

```eval_rst
.. toctree::
   :caption: Next Steps
   :maxdepth: 1
   :titlesonly:

   ../labs/libvirt.md
   ../labs/clab.md
```
