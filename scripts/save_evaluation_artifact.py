"""Local source-only entry point; this is not an installed farm CLI command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluation_tools.artifacts import main

if __name__ == "__main__":
    raise SystemExit(main())
