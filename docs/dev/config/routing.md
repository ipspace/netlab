# Generic Routing Tools Configuration Templates

This document describes the implementation details of the device configuration templates (and associated platform capabilities) needed to implement [](generic-routing):

* [Platform capabilities](dev-routing-platform)
* [Prefix filter data structure](dev-routing-prefix)
* [AS-Path filter data structure](dev-routing-aspath)
* [BGP community filter data structure](dev-routing-community)
* [Static routing data structure](dev-routing-static)
* [Routing policy data structure](dev-routing-policy)

<!--
Note to reviewers: the document describes the outputs of the transformation process, not the topology elements used as its input. The outputs might differ significantly from the inputs; you have to analyze the code to determine whether the outputs are correctly described.
-->

```{eval_rst}
.. include:: routing-platform.txt
```

```{eval_rst}
.. include:: routing-prefix.txt
```

```{eval_rst}
.. include:: routing-aspath.txt
```

```{eval_rst}
.. include:: routing-community.txt
```

```{eval_rst}
.. include:: routing-static.txt
```

```{eval_rst}
.. include:: routing-policy.txt
```
