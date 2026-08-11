(dev-documentation-url)=
# Adding Documentation URLs to log.error/log.warning calls

The `utils.log.error` function is the main error-reporting function (`warning` calls it, and `fatal` should as well). It can accept `doc_url` (pointer to relevant documentation) and `doc_url_text` (formatting of the hint text) among its many parameters. This document describes those two parameters.

The `doc_url` parameter points to the relevant documentation page. While you can use absolute URLs to point to non-netlab documentation, internal pointers should be relative URLs (`module/stp/`, not `https://netlab.tools/module/stp/`) and should include [an anchor](dev-documentation-url-anchor).

The `defaults.const.doc_url_prefix` topology default contains the _netlab_ documentation website URL (default: `https://netlab.tools/`) and can be changed by the user if they use a different website (for example, `https://ipspace.github.io/netlab/`) or an internal mirror.

(dev-documentation-url-anchor)=
The URL anchor should be taken from the Markdown text, not from the auto-generated website anchors. Sphinx generates heading anchors from heading text, which can change, whereas the source anchors do not. For example, do not use `module/stp/#global-parameters` (generated from heading text) to point to STP global parameters. Use `module/stp/#module-stp-global-params` (using Markdown anchor).

Finally, the documentation pointer is displayed with the green `[DOCS]` marker and the intro text derived from the `doc_url_text` parameter. Omitting that parameter will result in the standard text:

```text
[DOCS] See also: https://netlab.tools/module/stp/#module-stp-params
```

If you specify the `doc_url_text` parameter in `log.error` call (for example, `See {url} for the list of supported platforms`), you'll get a customized documentation pointer, for example:

```text
[DOCS] See https://netlab.tools/module/stp/#stp-platform for the list of supported platforms
```
