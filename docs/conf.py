"""Sphinx configuration for replus."""

from importlib.metadata import version as _version

project = "replus"
author = "Biagio Distefano"
copyright = "2022, Biagio Distefano"  # noqa: A001
release = _version("replus")
version = release

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "myst_parser",
    "sphinx_copybutton",
]

exclude_patterns = ["_build", "superpowers"]

html_theme = "furo"
html_title = f"replus {release}"

autodoc_member_order = "bysource"
autodoc_typehints = "description"

napoleon_google_docstring = True
napoleon_numpy_docstring = False

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

myst_enable_extensions = ["colon_fence"]
