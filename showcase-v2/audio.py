#!/usr/bin/env python3
"""Run the active revision PCM placement and BGM mixer."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().with_name("mix-revision-audio.py")), run_name="__main__")
