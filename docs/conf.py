# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
# sys.path.insert(0, os.path.abspath('.'))
import recommonmark
from recommonmark.transform import AutoStructify

# -- Project information -----------------------------------------------------

project = 'netlab'
copyright = '''2020–2023 Ivan Pepelnjak, Jeroen van Bemmel, Stefano Sasso, and
<a href="https://github.com/ipspace/netlab/graphs/contributors">other contributors</a>'''

author = 'Ivan Pepelnjak'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
#  'recommonmark',
# ones.

source_suffix = ['.rst', '.md']

extensions = [
  'myst_parser',
  'sphinxcontrib.jquery',
  'sphinx_rtd_dark_mode'
]

myst_heading_anchors = 3
default_dark_mode = False

myst_enable_extensions = [
    "deflist",
    "html_admonition",
    "replacements",
    "smartquotes",
    "strikethrough",
    "tasklist",
    "attrs_block"
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_context = {}
rtd_branch = os.environ.get("READTHEDOCS_VERSION", None)
html_context["w_dev"] = rtd_branch == "dev"
html_context["w_latest"] = rtd_branch == "latest"
html_show_sphinx = False
html_favicon = '_static/images/favicon.png'

on_rtd = os.environ.get("READTHEDOCS", None) == "True"

if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme

    html_theme = "sphinx_rtd_theme"
##    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
else:
    html_theme = "default"

html_theme_options = {
    'navigation_depth': 3
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
html_css_files = [ 'css/custom.css' ]

sys.path.insert(0, os.path.abspath('netlab'))

def setup(app):
    app.add_transform(AutoStructify)
