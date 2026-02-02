# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'joop'
copyright = '2025, Justin Rushin'
author = 'Justin Rushin'
release = '0.0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",  # Core autodoc extension
    "sphinx.ext.napoleon",  # For Google-style and NumPy-style docstrings
    "sphinx_autodoc_typehints",  # For type hints
]

# Configure autodoc
autodoc_default_options = {
    "members": True,  # Include class members
    "undoc-members": True,  # Include members without docstrings
    "private-members": False,  # Exclude private members (e.g., _method)
    "special-members": "__init__",  # Include special methods like __init__
    "inherited-members": True,  # Include inherited members
    "show-inheritance": True,  # Show class inheritance
}

# Napoleon settings (for Google/NumPy-style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',  # For Google-style or NumPy-style docstrings
    'sphinx.ext.autosummary',  # Enables recursive documentation
]