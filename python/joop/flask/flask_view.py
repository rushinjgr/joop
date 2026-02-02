"""Flask view integration for joop.

This module provides a base class for integrating joop views with Flask applications.

Any regular joop View can do multiple inheritance with a FlaskView to result
    in a class that can be used with Flask.

Functionality include jinja env proxying.

Classes:
    FlaskView:
        A base class for creating Flask-compatible views from joop View classes.
"""

from typing import Optional
from flask import Flask, current_app

from joop.web.view import View, Component

class FlaskView(View):
    """
    A base class for creating Flask-compatible views from joop View classes.

    This class provides methods to integrate joop views with Flask applications by
    adding URL rules and accessing the Flask Jinja2 environment.

    Use multiple inheritance to make your View a FlaskView ex.

    `class FlaskHello(HelloView, FlaskView):`


    Methods:
        _add_to_app(app: Flask, view_func: callable):
            Adds the view to a Flask application with the specified view function.

        _get_jinja_env():
            Retrieves the Jinja2 environment from the current Flask application context.
    """

    @classmethod
    def _add_to_app(cls, app: Flask, view_func: callable):
        """
        Add the view to a Flask application with the specified view function.

        Args:
            app (Flask): The Flask application instance.
            view_func (callable): The view function to associate with the URL rule.

        This method registers a URL rule with the Flask application, associating it
        with the specified view function and HTTP methods defined in the Endpoint.
        """
        app.add_url_rule(
            rule=cls.Endpoint._url,  # URL rule as a string
            endpoint=cls.Endpoint._name,  # Endpoint name
            view_func=view_func,  # The view function to call
            methods=cls.Endpoint._methods  # List of HTTP methods allowed
        )
    
    @classmethod
    def _get_jinja_env(cls):
        """
        Retrieve the Jinja2 environment from the current Flask application context.

        Returns:
            jinja2.Environment: The Jinja2 environment associated with the current
            Flask application context.

        This method allows joop views to access the Jinja2 environment configured
        for the Flask application.
        """
        return current_app.jinja_env