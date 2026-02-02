#!/usr/bin/env python

"""High-level test suite. Currently, verifies that the CLI works.."""


import unittest
from click.testing import CliRunner

from joop.cli import main


class TestJoop(unittest.TestCase):
    """Tests for `joop` package."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_001_command_line_interface(self):
        """Test the CLI."""
        runner = CliRunner()
        result = runner.invoke(main)
        assert result.exit_code == 0
        assert 'Hello World' in result.output
        help_result = runner.invoke(main, ['--help'])
        assert help_result.exit_code == 0
        assert '--help      Show this message and exit.' in help_result.output
