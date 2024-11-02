(extool-edgeshark)=
# Edgeshark

Edgeshark discovers the virtual communication on container hosts and can provide live capture with Wireshark with a single click.
The capture function requires the installation of the [cshargextcap](https://github.com/siemens/cshargextcap) Wireshark plugin. The [plugin repository](https://github.com/siemens/cshargextcap) provides detailed installation instructions for multiple platforms.

Add the following lines to a lab topology file to use Edgeshark with _netlab_:

```
tools:
  edgeshark:
```

**Notes:**

* Edgeshark can capture traffic on virtual interfaces but not on *libvirt* point-to-point tunnels ([more details](libvirt-capture)).
* A single instance of Edgeshark can discover the virtual communication of all labs running on your server.
* If you use the [multilab plugin](plugin-multilab), enable Edgeshark in a single (preferably dedicated) lab instance.
* The Edgeshark containers will be stopped when the netlab lab instance that started them is shut down. 
* Edgeshark works with a subset of _netlab_-supported platforms. _netlab_ does not check whether Edgeshark supports all the devices used in the lab topology.
