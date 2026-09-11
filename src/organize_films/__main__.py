"""Support ``python -m organize_films`` in addition to the installed command."""

import sys

from organize_films.cli import main

if __name__ == "__main__":
    sys.exit(main())
