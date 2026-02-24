import click

from mersea.editor import run


@click.command()
@click.argument("file", type=click.Path(exists=True))
def main(file):
    """Open a Mermaid diagram in the visual editor."""
    run(file)
