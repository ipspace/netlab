(extool-edgeshark)=
# Edgeshark

Edgeshark discovers the virtual communication on container hosts and can provide live capture with Wireshark with a single click.
Capture function requires installation of [cshargextcap](https://github.com/siemens/cshargextcap) Wireshark plugin. 
Detailed plugin installation instructions for multiple platforms are provided by the upstream.

* Add the following lines to the lab topology file to use Edgeshark with _netlab_:

```
tools:
  edgeshark:
```

**Notes:**

* A single instance of Edgeshark can discover the virtual communication of one or more labs on the host.
* If you are running multilabs with netlab and want to use the tool, enable Edgeshark as a tool in just one of them, preferably the longest lived one.
* The Edgeshark instance will be broken down when the netlab lab instance that started it is broken down. 
* Edgeshark supports a subset of _netlab_-supported platforms. _netlab_ does not check whether Edgeshark supports all the devices used in the lab topology.
