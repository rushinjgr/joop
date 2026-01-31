"""Flask testing module for joop.

This module provides functionality to start a Flask webserver for testing and development purposes.

Important: The test joop env is set as the jinja env for the Flask server. This is specific and desirable
    though your project may implement the environment otherwise.

Functions:
    start_test_flask():
        Starts the Flask webserver in debug mode using the `app` instance from `joop.flask`.

Dependencies:
    - Flask: Ensure Flask is installed. If not, install it using `pip install joop[flask]`.

Usage:
    - Import the `start_test_flask` function and call it to start the Flask webserver.

"""

from joop.tests.test_templater import environment
try:
    from joop.flask import app

    joop_env = environment


    def start_test_flask():
        global app

        app.run(debug=True)

except ImportError as e:
    raise ImportError(
        "The 'flask' module requires additional dependencies. "
        "Install them using 'pip install joop[flask]'."
    )
