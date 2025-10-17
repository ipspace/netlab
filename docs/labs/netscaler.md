(build-netscaler)=
# Using a Netscaler Container

We tested Netscaler release 13.1 and made the Dockerfile needed to build a container that's easy to start in _netlab_ available as part of _netlab_ release 25.11.

To add a Netscaler node to a _netlab_ lab topology:

* Build a local **netlab/netscaler** container with `netlab clab build netscaler`
* Use a Linux device with the **netlab/netscaler** image to add the load balancer to a lab topology:

```
nodes:
  lb1:
    provider: clab
    device: linux
    image: netlab/netscaler    
```

* You'll get a bash shell when you connect to a Netscaler node with **netlab connect**. Use the **nscli** command to start the Netscaler CLI
* Use username `clab` and password `clab@123` to log into the Netscaler CLI

You'll find even more details [here](https://github.com/ipspace/netlab/discussions/2732).
