# Creating Reports with Custom Output Formats

The *report* output module uses its parameter as the name of a Jinja2 formatting template and uses that template to create a custom report. For example, `netlab create -o report:addressing` creates an IP addressing report.

The *report* output module tries to use the **defaults.outputs.report.*rname*** topology setting (*rname* is the report name). If that fails, it tries to read the Jinja2 template from **_rname_.j2** file in **reports** subdirectory of the current directory, user _netlab_ directory (`~/.netlab`), system _netlab_ directory (`/etc/netlab`) and _netlab_ package directory.

## Built-In Reports

_netlab_ ships with built-in reports that describe physical wiring, node/interface or link/interface addressing, BGP AS numbers and BGP neighbors, management IP addresses, or OSPF areas.

Use the **[netlab show reports](netlab-show-reports)** command to display up-to-date list of available system reports

## Generating HTML reports

If a report name includes `.html`, _netlab_ assumes the template generates HTML markup and adds an HTML wrapper generated from `page.html.j2` to the generated text. The `page.html.j2` template included with _netlab_ contains the `head` and `body` HTML tags and a simple CSS style definition.

If you want to customize the HTML reports, add `page.html.j2` to one of the user directories the _reports_ module searches when locating the template file (see above). Your HTML wrapper might include inline CSS (using the `style` tag) or a link to an external stylesheet.

## Generating ASCII reports from Markdown

If a report name ends with `.ascii`, _netlab_ assumes you want to generate ASCII text from the corresponding Markdown report. 

It replaces the `.ascii` suffix with `.md`, uses the resulting template to generate the Markdown text, and renders it with the [rich.markdown](https://rich.readthedocs.io/en/stable/markdown.html) library.
