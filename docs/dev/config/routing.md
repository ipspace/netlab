# Generic Routing Tools Configuration Templates

This document describes the implementation details of the device configuration templates (and associated platform capabilities) needed to implement [](generic-routing):

* [Platform capabilities](dev-routing-platform)
* [Prefix filter data structure](dev-routing-prefix)
* [AS-Path filter data structure](dev-routing-aspath)
* [BGP community filter data structure](dev-routing-community)
* [Routing policy data structure](dev-routing-policy)
* [Static routing data structure](dev-routing-static)

<!--
Note to reviewers: the document describes the outputs of the transformation process, not the topology elements used as its input. The outputs might differ significantly from the inputs; you have to analyze the code to determine whether the outputs are correctly described.
-->

```{include} routing-platform.txt
```
```{include} routing-prefix.txt
```
```{include} routing-aspath.txt
```
```{include} routing-community.txt
```
```{include} routing-policy.txt
```
```{include} routing-static.txt
```
