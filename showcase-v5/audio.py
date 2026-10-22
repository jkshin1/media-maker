#!/usr/bin/env python3
"""Build Revision5 music while preserving the approved narration and hero audio."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().with_name("mix-v5-audio.py")),run_name="__main__")
