"""Console script for joop."""
import sys
import click

from joop import hello_world

@click.command()
def main(args=None):
    """Console script for joop."""
    click.echo(hello_world())
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
