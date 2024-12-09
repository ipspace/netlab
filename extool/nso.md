(tools-nso)=
# Cisco NSO

Cisco NSO is a tool for multi vendor network automation. See https://cisco-tailf.gitbook.io/nso-docs for documentation.

## Installation

* Download the docker container and any NEDs from https://software.cisco.com/download/home/286331591/type. You can also use NEDs from 3rd parties or make your own. 
* You need to extract the docker image and load and tag it in docker. See the commands below.

```
sh nso-6.4-freetrial.container-image-prod.linux.x86_64.signed.bin
docker load -i nso-6.4.container-image-prod.linux.x86_64.tar.gz
docker tag cisco-nso-prod:6.4 cisco-nso-prod
```

**Notes:**
* The download is a 90 Day trial.
* You can also provide your own docker image or add a license following the Cisco documentation.
* You must update the Docker tag when switching to a new version

## Using NSO

* Add the following lines to the lab topology file to enable NSO.

```
tools:
  nso:
```

* The URL used to connect to NSO is printed during **netlab up** process. 
* You can connect to the CLI with the **netlab connect nso** command. You can edit the NSO configs this way and access the Cisco NSO CLI with the `ncs_cli -C -u admin` command.
* You have to reload NSO after making configuration changes with the `ncs --reload` command.

**Notes:**
* Username is admin and password is admin.
* The Cisco NSO tool was tested with with production image of release 6.4. The development image is used for creating NEDs.
* WebUI and Local Authentication have been enabled and NED Package upload has been enabled by the WebUI.
* Data collected by NSO is stored on a lab-specific Docker volume and remains intact across lab runs until you execute the **netlab down --cleanup** command.
