"""Unit tests for joop Flask integration.

This module contains unit tests for the Flask views in the joop project. It uses the
unittest framework and Flask's test_client to test the functionality of the views.

It borders on being an integration test, insofar as we are testing:
* joop's views
* joop's templater
* joop's flask integration

Classes:
    TestView:
        Test cases for the Flask views in the joop application.

"""

import unittest

try:
    from joop.flask import app
    APP_AVAILABLE = app is not None
except ImportError:
    APP_AVAILABLE = False

@unittest.skipIf(not APP_AVAILABLE, "joop.flask or app is not available")
class TestView(unittest.TestCase):
    """
    Test cases for the Flask views in the joop application.

    This test class uses the Flask test client to send requests to the application
    and verify the responses.

    Methods:
        setUp():
            Sets up the test client for the Flask application.

        test_000_hello():
            Tests the '/hello' endpoint to ensure it returns a 200 status code.
    """

    def setUp(self):
                self.client = app.test_client()

    def test_000_hello(self):
        response = self.client.get('/hello') 
        self.assertEqual(response.status_code, 200)
