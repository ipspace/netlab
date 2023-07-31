# Creating Reports with Custom Output Formats

The *report* output module uses its parameter as the name of a Jinja2 formatting template that is used to create a custom report. For example, `netlab create -o report:addressing` creates an IP addressing report.

The *report* output module tries to use the **defaults.outputs.report.*rname*** topology setting (*rname* is the report name). If that fails, it tries to read the Jinja2 template from **_rname_.j2** file in **reports** subdirectory of current directory, user _netlab_ directory (`~/.netlab`), system _netlab_ directory (`/etc/netlab`) and _netlab_ package directory.

## Built-In Reports

_netlab_ ships with the following built-in reports:

* **addressing** -- Node/interface addressing report in text format
* **addressing.html** -- Node/interface and link/interface addressing report in HTML format
* **addressing.node.html** -- Node/interface addressing report in HTML format
* **addressing.link.html** -- Link/interface addressing report in HTML format

```{note}
The **[netlab show reports](show-reports)** command displays up-to-date list of available system reports
```

## Generating HTML reports

If a report name includes `.html`, _netlab_ assumes the template generates HTML markup and adds HTML wrapper generated from `page.html.j2` to the generated text. The `page.html.j2` template included with _netlab_ contains the `head` and `body` HTML tags and a simple CSS style definition.

If you want to customize the HTML reports, add `page.html.j2` to  one of the user directories the _reports_ module searches when trying to locate the template file (see above). Your HTML wrapper might include inline CSS (using the `style` tag) or a link to an external stylesheet.
