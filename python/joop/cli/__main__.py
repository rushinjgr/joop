"""Console script for joop development and testing purposes.

Includes:

- A hello world for the CLI.
- Start a Flask webserver for testing purposes using the `--flask-server` option.
- Display a help menu with usage instructions using the `--help` or `-h` options.

Usage:
    - Run the CLI normally: `python -m joop.cli`
    - Start the Flask webserver: `python -m joop.cli --flask-server`
    - Display the help menu: `python -m joop.cli --help`

"""
import sys
import click
from joop.cli.test_flask import start_test_flask

from joop import hello_world

@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option('--flask-server', is_flag=True, help="Spin up a Flask webserver for testing.")
def main(flask_server, args=None):
    """Console script for joop.

    Usage:
      - Run the CLI normally: `python -m joop.cli`
      - Start the Flask webserver: `python -m joop.cli --flask-server`
      - Display the help menu: `python -m joop.cli --help`
    """
    if flask_server:
        click.echo("Starting Flask webserver...")
        start_test_flask()
    else:
        click.echo(hello_world())
    return 0

if __name__ == "__main__":
    main()
