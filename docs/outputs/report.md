# Creating Reports with Custom Output Formats

The *report* output module uses its parameter as the name of a Jinja2 formatting template that is used to create a custom report. For example, `netlab create -o report:addressing` creates an IP addressing report.

The *report* output module tries to use the **defaults.outputs.report.*rname*** topology setting (*rname* is the report name). If that fails, it tries to read the Jinja2 template from **_rname_.j2** file in **reports** subdirectory of current directory, user _netlab_ directory (`~/.netlab`), system _netlab_ directory (`/etc/netlab`) and _netlab_ package directory.

_netlab_ ships with the following built-in reports:

* **addressing** -- Node/interface addressing report
