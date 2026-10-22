#!/usr/bin/env python3
"""Reproduce the Revision9 mix from its verified full original narration."""
from pathlib import Path
import runpy

if __name__=='__main__':
    runpy.run_path(str(Path(__file__).resolve().with_name('mix-v9-audio.py')),run_name='__main__')
