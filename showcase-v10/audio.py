#!/usr/bin/env python3
"""Rebuild approved Revision10 placement, pitch-only voice and locked music."""
from pathlib import Path
import importlib.util
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
if importlib.util.find_spec('numpy') is None:
    candidates=[ROOT.parent/'.venv/bin/python3',Path('/Users/jk/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3')]
    runtime=next((p for p in candidates if p.exists() and p.resolve()!=Path(sys.executable).resolve() and subprocess.run([str(p),'-c','import numpy'],capture_output=True).returncode==0),None)
    if runtime is None: raise SystemExit('NumPy is required. Install NumPy or use a Python environment that includes it.')
    os.execv(str(runtime),[str(runtime),str(__file__),*sys.argv[1:]])
script=ROOT/'mix-v10-audio.py'
os.execv(sys.executable,[sys.executable,str(script),*sys.argv[1:]])
