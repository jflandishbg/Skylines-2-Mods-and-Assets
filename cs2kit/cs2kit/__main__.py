"""CLI entrypoint for `python -m cs2kit`."""
import sys
from .runner import main

if __name__ == "__main__":
    raise SystemExit(main())
