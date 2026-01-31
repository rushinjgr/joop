"""Templater testing module for joop.

This module instantiates a jinja templating engine for development and testing purposes.
    It's not just restricted to automated testing.

Classes:
    BaseTestHTMLComponent:
        A base class for testing HTML components.

Variables:
    environment:
        A placeholder variable for the templating environment.

Usage:
    - Utilize the `environment` variable for templating-related operations.

"""

from joop.web.templater import EnvironmentFactory
from jinja2 import FileSystemLoader
from joop.web.j_env import set_joop_env

from pathlib import Path

WEB_TEMPLATES_ROOT = Path("../templates/examples/")

environment = EnvironmentFactory.create_environment(
        loader=FileSystemLoader(WEB_TEMPLATES_ROOT)
    )

set_joop_env(environment)