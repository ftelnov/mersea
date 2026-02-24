import argparse
import sys
from pathlib import Path

from mersea.editor import run


def main():
    parser = argparse.ArgumentParser(description="Open a Mermaid diagram in the visual editor.")
    parser.add_argument("file", help="Path to .mmd file")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    run(str(path))
