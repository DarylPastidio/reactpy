# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/master/config

import sys
from pathlib import Path


# -- Path Setup --------------------------------------------------------------

here = Path(__file__).parent

# project path
sys.path.insert(0, str(here.parent.parent))

# extension path
sys.path.insert(0, str(here / "_exts"))


# -- Project information -----------------------------------------------------

project = "IDOM"
copyright = "2020, Ryan Morshead"
author = "Ryan Morshead"

# -- Common External Links ---------------------------------------------------

extlinks = {
    "issue": ("https://github.com/idom-team/idom/issues/%s", "#"),
    "pull": ("https://github.com/idom-team/idom/pull/%s", "#"),
    "discussion": ("https://github.com/idom-team/idom/discussions/%s", "#"),
    "commit": ("https://github.com/idom-team/idom/commit/%s", ""),
}

# -- General configuration ---------------------------------------------------

# If your documentatirston needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.coverage",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.extlinks",
    "sphinx.ext.autosectionlabel",
    # third party extensions
    "sphinx_copybutton",
    "sphinx_reredirects",
    "sphinx_design",
    # custom extensions
    "async_doctest",
    "autogen_api_docs",
    "copy_vdom_json_schema",
    "interactive_widget",
    "patched_html_translator",
    "widget_example",
    "build_custom_js",
]

# Add any paths that contain templates here, relative to this directory.
# templates_path = ["templates"]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "_custom_js",
]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = None

# The default language to highlight source code in.
highlight_language = "python3"

# Controls how sphinx.ext.autodoc represents typehints in the function signature
autodoc_typehints = "description"

# -- Extension Configuration ------------------------------------------------------

# -- MyST Parser --

myst_enable_extensions = [
    # "amsmath",
    "colon_fence",
    # "deflist",
    # "dollarmath",
    # "html_admonition",
    # "html_image",
    # "linkify",
    # "replacements",
    # "smartquotes",
    # "substitution",
    # "tasklist",
]

# -- sphinx_panel --

# Used to stop the extension from loading bootstrap twice since the `pydata_sphinx_theme`
# already adds it for use.
panels_add_bootstrap_css = False

# -- sphinx.ext.autodoc --

# show base classes for autodoc
autodoc_default_options = {
    "show-inheritance": True,
    "member-order": "bysource",
}
# order autodoc members by their order in the source
autodoc_member_order = "bysource"

# -- sphinx_reredirects --

redirects = {
    "package-api": "_autogen/user-apis.html",
    "configuration-options": "_autogen/dev-apis.html#configuration-options",
    "examples": "creating-interfaces/index.html",
}

# -- Options for HTML output -------------------------------------------------

# Set the page title
html_title = "IDOM Docs"

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"
html_logo = "_static/branding/idom-logo.svg"
html_favicon = "_static/branding/idom-logo-square-small.svg"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# These paths are either relative to html_static_path
# or fully qualified paths (eg. https://...)
css_dir = here / "_static" / "css"
html_css_files = [str(p.relative_to(here / "_static")) for p in css_dir.glob("*.css")]

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# The default sidebars (for documents that don't match any pattern) are
# defined by theme itself.  Builtin themes are using these templates by
# default: ``['localtoc.html', 'relations.html', 'sourcelink.html',
# 'searchbox.html']``.
#
# html_sidebars = {}


# -- Options for Sphinx Panels -----------------------------------------------

panels_css_variables = {
    "tabs-color-label-active": "rgb(106, 176, 221)",
    "tabs-color-label-inactive": "rgb(201, 225, 250)",
    "tabs-color-overline": "rgb(201, 225, 250)",
    "tabs-color-underline": "rgb(201, 225, 250)",
}

# -- Options for HTMLHelp output ---------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = "IDOMdoc"


# -- Options for LaTeX output ------------------------------------------------

# latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#
# 'papersize': 'letterpaper',
# The font size ('10pt', '11pt' or '12pt').
#
# 'pointsize': '10pt',
# Additional stuff for the LaTeX preamble.
#
# 'preamble': '',
# Latex figure (float) alignment
#
# 'figure_align': 'htbp',
# }

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [(master_doc, "IDOM.tex", html_title, "Ryan Morshead", "manual")]


# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [(master_doc, "idom", html_title, [author], 1)]


# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        master_doc,
        "IDOM",
        html_title,
        author,
        "IDOM",
        "One line description of project.",
        "Miscellaneous",
    )
]

# -- Options for Sphinx-Autodoc-Typehints output -------------------------------------------------

set_type_checking_flag = False

# -- Options for Epub output -------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = project

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#
# epub_identifier = ''

# A unique identification for the text.
#
# epub_uid = ''

# A list of files that should not be packed into the epub file.
epub_exclude_files = ["search.html"]

# -- Options for intersphinx extension ---------------------------------------

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    "https://docs.python.org/": None,
    "pyalect": ("https://pyalect.readthedocs.io/en/latest", None),
    "sanic": ("https://sanic.readthedocs.io/en/latest/", None),
    "tornado": ("https://www.tornadoweb.org/en/stable/", None),
    "flask": ("https://flask.palletsprojects.com/en/1.1.x/", None),
}

# -- Options for todo extension ----------------------------------------------

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True
