#!/usr/bin/env python3
"""Decode the approved mix for inspection; the final mux copies its AAC stream."""
from pathlib import Path
import subprocess
HERE=Path(__file__).resolve().parent;OUT=HERE.parent/'out/showcase-v3'
OUT.mkdir(parents=True,exist_ok=True)
subprocess.run(['ffmpeg','-y','-v','error','-i',str(HERE/'narration/approved-mix.m4a'),'-vn','-c:a','pcm_s16le',str(OUT/'audio.wav')],check=True)
print('Decoded approved mix for inspection; no new narration or music processing.')
