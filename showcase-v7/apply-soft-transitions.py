#!/usr/bin/env python3
"""Compose the lossless transition patch while copying the original AAC audio."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'out/showcase'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    source = OUT / 'RD_Process_AI_Fast_Track_Showcase.mp4'
    patch = OUT / 'transition-patch.mov'
    target = OUT / 'RD_Process_AI_Fast_Track_Showcase_Soft_Transitions.mp4'
    temporary = target.with_suffix('.partial.mp4')
    metadata = json.loads((OUT / 'soft-transitions-metadata.json').read_text())
    timeline = json.loads((HERE / 'timeline.json').read_text())
    original_hash, overlay_hash = sha(source), sha(patch)
    assert metadata['test_only'] is False
    assert metadata['source_video_sha256'] == original_hash
    assert metadata['overlay_sha256'] == overlay_hash
    assert metadata['overlay_frames'] == timeline['frames']
    ffmpeg = shutil.which('ffmpeg')
    assert ffmpeg, 'ffmpeg is required'
    cmd = [ffmpeg, '-y', '-hide_banner', '-loglevel', 'warning', '-stats',
           '-i', str(source), '-i', str(patch),
           '-filter_complex', '[0:v][1:v]overlay=x=0:y=0:format=auto:shortest=1,format=yuv420p[v]',
           '-map', '[v]', '-map', '0:a:0', '-frames:v', str(timeline['frames']),
           '-c:v', 'libx264', '-preset', 'fast', '-crf', '16', '-pix_fmt', 'yuv420p',
           '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
           '-c:a', 'copy', '-movflags', '+faststart', str(temporary)]
    subprocess.run(cmd, check=True)
    assert sha(source) == original_hash, 'Original video changed'
    assert sha(patch) == overlay_hash, 'Transition patch changed'
    temporary.replace(target)
    report = {'status': 'COMPOSED_PENDING_VALIDATION', 'file': str(target),
              'sha256': sha(target), 'bytes': target.stat().st_size,
              'source_sha256': original_hash, 'patch_sha256': overlay_hash,
              'frames': timeline['frames'], 'audio_mode': 'AAC stream copy',
              'transition_seconds': metadata['transition_seconds'],
              'gold_sweep_removed': metadata['gold_sweep_removed']}
    (OUT / 'soft-transitions-composition.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))

if __name__ == '__main__':
    main()
