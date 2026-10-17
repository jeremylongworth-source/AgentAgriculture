"""Source-checkout entry point; the installed command is agent-agriculture."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent_agriculture.cli import main

raise SystemExit(main())
