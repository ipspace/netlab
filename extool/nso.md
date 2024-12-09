(tools-nso)=
# NSO

NSO is a tool for multi vendor network automation. See https://cisco-tailf.gitbook.io/nso-docs for documentation.

* Add the following lines to the lab topology file to enable NSO.

```
tools:
  nso:
```
* The URL used to connect to NSO is printed during **netlab up** process. 
* You can connect to the cli with the **netlab connect nso** command. You can edit the NSO configs this way and access the cisco NSO cli with the following command ncs_cli -C -u admin. Config changes need NSO reloaded with the ncs --reload command.
* You need to download the docker container and any NEDs from https://software.cisco.com/download/home/286331591/type. You can also use NEDs from 3rd parties or make your own. The download is a 90 Day trial you can also provide your own docker image or add a license following the cisco documentation.
* The docker container download this was tested with is 6.4 and the Production image, the development image is used for creating NEDs.


**Notes:**
* Data collected by NSO is stored on a lab-specific Docker volume and remains intact across lab runs until you execute the **netlab down --cleanup** command.
* Username is admin and password is admin.
* WebUI and Local Authentication have been enabled and NED Package upload has been enabled by the WebUI.
