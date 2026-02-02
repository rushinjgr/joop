"""Flask application initialization module for joop.

This is used for example, development, and testing purposes.
This module initializes a Flask application and configures it with the joop Jinja2 environment.
That is important. ^^^ We are not using the default Jinja2 env, and that is intentional.
This is the place to register example Flask views to the application.

Attributes:
    app (Flask): The Flask application instance.

Modules:
"""

from __future__ import absolute_import
from flask import Flask
from joop.web.j_env import joop_env
from joop.flask.example import (
    FlaskHello, FlaskName, FlaskTable
)

app = Flask(__name__)

# Configure the Jinja2 environment for the Flask application
# Important to do this and not use the default.
app.jinja_env = joop_env

# Register example views to the Flask application
# ex. MyView.add_to_app(app)
FlaskHello.add_to_app(app)
FlaskName.add_to_app(app)
FlaskTable.add_to_app(app)
