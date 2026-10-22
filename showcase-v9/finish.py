#!/usr/bin/env python3
"""Encode verified narration once, copy video, and decode the final film."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / 'out/showcase-v9'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def streamhash(path):
    return subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path),
        '-map', '0:v:0', '-c', 'copy', '-f', 'hash', '-hash', 'sha256', '-'], text=True).strip()


def main():
    required = [ROOT / 'timeline.json', OUT / 'render-validation.json',
                OUT / 'audio-validation.json', OUT / 'narration-coverage-validation.json']
    missing = [str(p) for p in required if not p.exists()]
    assert not missing, 'Final production is not ready: ' + ', '.join(missing)
    tl, render, audio, speech = [json.loads(p.read_text()) for p in required]
    assert tl['revision'] == 9 and not tl.get('preview_only') and tl['tempo'] == 1
    assert 0 < tl['duration'] <= min(315, tl['max_seconds'])
    assert all(r['status'] == 'PASS' for r in [render, audio, speech])
    assert not render.get('preview_only') and audio['tempo'] == 1
    authorization = ROOT / 'narration/recovery/authorization.json'
    approved = json.loads(authorization.read_text())
    assert approved['authorization_source'] == 'direct_user_reply_in_current_chat'
    assert approved['voice_speed_ratio'] == 1 and approved['max_video_seconds'] == 315
    assert audio.get('ending_reuse_exception_authorized') is True
    assert audio.get('generation_mode') == 'single_take_with_authorized_original_ending_reuse'
    assert audio.get('fresh_body_narration') is True
    for row in render['inputs'] + audio['input_bindings']:
        assert sha(ROOT / row['file']) == row['sha256'], row['file']
    silent, pcm = OUT / 'video_silent.mp4', OUT / 'audio.wav'
    assert sha(silent) == render['sha256'] and sha(pcm) == audio['audio_sha256']
    video = OUT / 'RD_Process_AI_Fast_Track_Showcase_Revision9.mp4'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(silent), '-i', str(pcm),
        '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
        '-ar', '48000', '-ac', '2', '-movflags', '+faststart', str(video)], check=True)
    meta = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
        '-show_format', '-of', 'json', str(video)]))
    v = next(s for s in meta['streams'] if s['codec_type'] == 'video')
    a = next(s for s in meta['streams'] if s['codec_type'] == 'audio')
    checks = {'video_stream_copied': streamhash(video) == streamhash(silent),
              'frames_match': int(v['nb_frames']) == tl['frames'],
              'full_hd_30fps': v['width'] == 1920 and v['height'] == 1080 and v['r_frame_rate'] == '30/1',
              'aac_48k_stereo': a['codec_name'] == 'aac' and a['sample_rate'] == '48000' and a['channels'] == 2,
              'duration_matches': abs(float(meta['format']['duration']) - tl['duration']) < 1 / 30,
              'hard_max_315_seconds': float(meta['format']['duration']) <= 315.001,
              'no_speech_speedup': audio['tempo'] == 1,
              'all_68_narration_lines_verified': speech['status'] == 'PASS'}
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(video), '-f', 'null', '-'], check=True)
    checks['whole_audio_video_decode'] = True
    result = {'revision': 9, 'status': 'PASS' if all(checks.values()) else 'FAIL',
              'checks': checks, 'final_sha256': sha(video), 'silent_video_sha256': sha(silent),
              'pcm_mix_sha256': sha(pcm), 'narration_coverage_sha256': sha(required[-1]),
              'duration_seconds': tl['duration'], 'frames': tl['frames'],
              'new_full_tts': False, 'fresh_body_narration': True,
              'ending_reuse_exception_authorized': True,
              'recovery_authorization_sha256': sha(authorization),
              'generation_mode': 'single_take_with_authorized_original_ending_reuse', 'tempo': 1,
              'method': 'Current verified silent video copied; verified new body plus approved original-speed ending and music PCM encoded once to AAC; whole output strictly decoded.'}
    (OUT / 'mux-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'file': str(video), **result}, ensure_ascii=False))
    assert all(checks.values())


if __name__ == '__main__':
    main()
