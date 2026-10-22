#!/usr/bin/env python3
"""Build the approved Revision4 slower narration and saved BGM mix."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().with_name("mix-v4-audio.py")),run_name="__main__")
