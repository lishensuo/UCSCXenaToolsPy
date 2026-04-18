"""Sphinx configuration for UCSCXenaToolsPy."""

import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

# ── Project ───────────────────────────────────────────────────────────────

project = "UCSCXenaToolsPy"
copyright = "2026, Shixiang Wang"
author = "Shixiang Wang"
release = "0.1.0"

# ── Extensions ────────────────────────────────────────────────────────────

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_autodoc_typehints",
]

# ── Templates and Static ──────────────────────────────────────────────────

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# ── Theme ─────────────────────────────────────────────────────────────────

html_theme = "furo"

# ── Napoleon (Google-style docstrings) ────────────────────────────────────

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_use_param = True
napoleon_use_rtype = True

# ── Autodoc ───────────────────────────────────────────────────────────────

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "private-members": False,
    "show-inheritance": True,
}
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented"

# ── MyST ──────────────────────────────────────────────────────────────────

myst_enable_extensions = [
    "colon_fence",
    "dollarmath",
    "linkify",
]

# ── Intersphinx ───────────────────────────────────────────────────────────

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable", None),
}
