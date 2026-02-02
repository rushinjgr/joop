# joop

[![image](https://img.shields.io/pypi/v/joop.svg)](https://pypi.python.org/pypi/joop)

**OOP Paradigms with an emphasis on DAO patterns, HTMX, and AlpineJS.**


-   Free software: Apache Software License 2.0
-   Documentation: https://rushinjgr.github.io/joop
    

## Features

-   HTML Components for server-side rendering.

## Getting Started

### Setting Up a Virtual Environment

It is recommended to use `poetry` to manage the virtual environment and dependencies. Follow these steps:

1. Install `poetry` globally if it is not already installed:

   ```bash
   pip install poetry
   ```

2. Install the Poetry Shell plugin to enable the `poetry shell` command:

   ```bash
   poetry self add poetry-plugin-shell
   ```

3. Use `poetry` to install all dependencies (including development tools like `twine`):

   ```bash
   poetry install
   ```

   This will automatically create a virtual environment in the `.venv` folder inside the project directory, as specified in the `poetry.toml` file.

4. To activate the virtual environment, use:

   ```bash
   poetry shell
   ```

### Build commands

1. Run `poetry check` to validate the `pyproject.toml` file:

   ```bash
   poetry check
   ```

2. Build the package using `python -m build`:

   ```bash
   poetry run python -m build
   ```

   This will generate distribution files in the `dist/` directory.

3. Verify the distribution files using `twine check`:

   ```bash
   poetry run twine check dist/*
   ```

   This ensures the distribution files are ready for upload to PyPI.

### Building the Documentation

To build the documentation, follow these steps:

1. Ensure all dependencies, including development dependencies, are installed:
   ```bash
   poetry install --with dev
   ```

2. Build the documentation using Sphinx:
   ```bash
   poetry run sphinx-build -b html docs/source docs/build/html
   ```

   The generated HTML files will be located in the `docs/build/html` directory.

3. Open the documentation in your browser by navigating to:
   ```
   docs/build/html/index.html
   ```

## Commands

For all commands, run in `joop/python`

To run the CLI: `python -m joop.cli`

For tests, run `python -m unittest joop.tests` (add `-vvv` to see output)

For coverage, run:
```
coverage run -m unittest joop.tests
coverage report
```
