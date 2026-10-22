#!/usr/bin/env python3
"""Build/check a separate WMV8/WMA2 compatibility fallback, never the source.

Run with --validate-existing for an already encoded partial. Inspect the three
generated visual samples, record visual_review.status=PASS in the receipt, then
use --finalize. Windows Media Player runtime acceptance is never inferred.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
OUT = PROJECT / 'out/showcase-v12/windows10'
SOURCE = PROJECT / 'out/showcase-v12/RD_Process_AI_Fast_Track_Showcase_Revision12.mp4'
PCM = PROJECT / 'out/showcase-v12/audio.wav'
NAME = 'RD_Process_AI_Fast_Track_Revision12_Windows10_Fallback'
PARTIAL, FINAL = OUT / (NAME + '.partial.wmv'), OUT / (NAME + '.wmv')
REPORT = OUT / 'wmv-validation.json'
SR = 48000
SOURCE_SHA = '8554cff5a71b81be36734c18a763f2aa94db36b3198d29984ac815325ffb972b'
PCM_SHA = '918001d368764056710e7fbccd6db170424b796b71ac1c9a43914cbc2650bfb7'


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def run(args, binary=False):
    return subprocess.run([str(a) for a in args], capture_output=True,
                          text=not binary, check=True)


def save(p, value):
    Path(p).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                 allow_nan=False) + '\n')


def relative(p):
    return Path(p).resolve().relative_to(PROJECT).as_posix()


def command():
    return ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'warning', '-i', SOURCE,
            '-i', PCM, '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'wmv2',
            '-q:v', '2', '-g', '60', '-bf', '0', '-pix_fmt', 'yuv420p',
            '-fps_mode', 'passthrough', '-c:a', 'wmav2', '-b:a', '192k',
            '-ar', '48000', '-ac', '2', '-map_metadata', '-1', '-f', 'asf', PARTIAL]


def probe(p):
    return json.loads(run(['ffprobe', '-v', 'error', '-show_streams',
                          '-show_format', '-of', 'json', p]).stdout)


def protected():
    status = PROJECT / 'SHOWCASE_STATUS.json'
    saved = json.loads(status.read_text())
    paths = [SOURCE, PCM, ROOT / 'timeline.json', status,
             PROJECT / saved['current_source_archive']]
    return {relative(p): sha(p) for p in paths}


def first_decoded_times(p):
    frames = json.loads(run(['ffprobe', '-v', 'error', '-read_intervals', '%+0.3',
                             '-show_frames', '-show_entries',
                             'frame=media_type,best_effort_timestamp_time,pts_time,nb_samples',
                             '-of', 'json', p]).stdout)['frames']
    result = {}
    for f in frames:
        kind = f['media_type']
        value = f.get('best_effort_timestamp_time', f.get('pts_time'))
        if kind in ['video', 'audio'] and kind not in result and value is not None:
            result[kind] = float(value)
    assert set(result) == {'video', 'audio'}
    return result


def audio_sync(p, first_times):
    decoded = run(['ffmpeg', '-v', 'error', '-xerror', '-err_detect', 'explode',
                   '-i', p, '-map', '0:a:0', '-ar', str(SR), '-ac', '2',
                   '-c:a', 'pcm_f32le', '-f', 'f32le', '-'], binary=True)
    y = np.frombuffer(decoded.stdout, dtype='<f4').reshape(-1, 2).mean(axis=1)
    with wave.open(str(PCM)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (SR, 2, 2)
        samples = w.getnframes()
        x = np.frombuffer(w.readframes(samples), dtype='<i2').reshape(-1, 2).mean(axis=1) / 32768
    rows = []
    for center in [5., samples / SR / 2, samples / SR - 7.]:
        start, n = round((center - 1) * SR), 2 * SR
        a, b = x[start:start + n].copy(), y[start:start + n].astype(np.float64)
        a -= a.mean()
        b -= b.mean()
        size = 1 << ((len(a) + len(b) - 1).bit_length())
        corr = np.fft.irfft(np.fft.rfft(b, size) * np.conj(np.fft.rfft(a, size)), size)
        lags = np.arange(-12000, 12001)
        lag = int(lags[np.argmax(corr[lags % size])])
        aligned = y[start + lag:start + lag + n].astype(np.float64)
        aligned -= aligned.mean()
        score = float(np.sum(a * aligned) / math.sqrt(np.sum(a * a) * np.sum(aligned * aligned)))
        effective = first_times['audio'] - first_times['video'] + lag / SR
        rows.append({'reference_seconds': [start / SR, (start + n) / SR],
                     'decoded_PCM_lag_samples': lag, 'decoded_PCM_lag_seconds': lag / SR,
                     'normalized_correlation': score, 'effective_audio_late_seconds': effective})
    lag = int(round(np.median([r['decoded_PCM_lag_samples'] for r in rows])))
    head = max(0, -lag)
    head_peak = float(np.max(np.abs(x[:head]))) if head else 0
    return {'first_decoded_frame_PTS_seconds': first_times,
            'definition': 'decoded[n] approximately reference[n-L]; actual audio-late offset=(first decoded audio PTS-first displayed video PTS)+L/48000. Stream.start_time is not substituted for decoded-frame PTS.',
            'probes': rows, 'decoded_samples': len(y), 'reference_samples': samples,
            'decoded_source_coverage_samples': [head, len(y) - lag],
            'initial_codec_unavailable_reference_samples': head,
            'initial_codec_unavailable_reference_peak_dbFS': 20 * math.log10(max(head_peak, 1e-15)),
            'full_reference_EOF_covered': len(y) - lag >= samples,
            'no_extra_audio_delay_or_tempo_filter_applied': True}


def validate():
    before = protected()
    assert sha(SOURCE) == SOURCE_SHA and sha(PCM) == PCM_SHA
    tl = json.loads((ROOT / 'timeline.json').read_text())
    assert tl['frames'] == 9724 and tl['fps'] == 30
    file = PARTIAL if PARTIAL.exists() else FINAL
    meta = probe(file)
    video = next(s for s in meta['streams'] if s['codec_type'] == 'video')
    audio = next(s for s in meta['streams'] if s['codec_type'] == 'audio')
    first = first_decoded_times(file)
    choices = [next(e for e in tl['entries'] if e['kind'] == 'title'),
               next(e for e in tl['entries'] if e.get('cut_id') == 'task16_cut3'),
               tl['entries'][-1]]
    frames = [(e['start_frame'] + e['end_frame']) // 2 for e in choices]
    selected = '+'.join(f'eq(n,{n})' for n in frames)
    images = OUT / 'wmv-review'
    images.mkdir(exist_ok=True)
    # One complete strict AV decode also writes the representative video frames.
    result = run(['ffmpeg', '-y', '-v', 'error', '-xerror', '-err_detect', 'explode',
                  '-i', file, '-filter_complex',
                  f"[0:v]split=2[full][sample];[sample]select='{selected}'[stills]",
                  '-map', '[full]', '-map', '0:a:0', '-f', 'null', '-',
                  '-map', '[stills]', '-fps_mode', 'vfr', '-c:v', 'png',
                  images / 'wmv-%02d.png', '-progress', 'pipe:1', '-nostats'])
    decoded_frames = int(re.findall(r'^frame=(\d+)', result.stdout, re.M)[-1])
    run(['ffmpeg', '-y', '-v', 'error', '-i', SOURCE, '-vf', f"select='{selected}'",
         '-frames:v', '3', '-fps_mode', 'vfr', '-c:v', 'png', images / 'source-%02d.png'])
    records = []
    for i, (entry, frame) in enumerate(zip(choices, frames), 1):
        source, sample = images / f'source-{i:02d}.png', images / f'wmv-{i:02d}.png'
        stat = run(['ffmpeg', '-v', 'info', '-i', source, '-i', sample,
                    '-lavfi', 'ssim', '-frames:v', '1', '-f', 'null', '-'])
        score = float(re.findall(r'All:([0-9.]+)', stat.stderr)[-1])
        records.append({'frame_index': frame, 'source_content_seconds': frame / 30,
                        'section_id': entry['section_id'], 'kind': entry['kind'],
                        'wmv_frame': relative(sample), 'wmv_frame_sha256': sha(sample),
                        'source_frame': relative(source), 'source_frame_sha256': sha(source),
                        'SSIM': score})
    sync = audio_sync(file, first)
    content_duration = decoded_frames / 30
    container_duration = float(meta['format']['duration'])
    checks = {
        'WMV8_WMA2_ASF': video['codec_name'] == 'wmv2' and video['codec_tag_string'] == 'WMV2' and audio['codec_name'] == 'wmav2' and meta['format']['format_name'] == 'asf',
        'fullHD420_30fps_no_Bframes': (video['width'], video['height'], video['pix_fmt'], video['avg_frame_rate'], video['has_b_frames']) == (1920, 1080, 'yuv420p', '30/1', 0),
        'WMA192k_48k_stereo': int(audio['bit_rate']) == 192000 and int(audio['sample_rate']) == SR and audio['channels'] == 2,
        'whole_strict_AV_decode_9724_frames': decoded_frames == 9724,
        'unchanged_video_content_duration': abs(content_duration - tl['duration']) < 1e-9,
        'ASF_container_overhead_under150ms': 0 <= container_duration - content_duration <= .15,
        'three_visual_samples_SSIM_above_point97': len(records) == 3 and min(r['SSIM'] for r in records) >= .97,
        'three_actual_audio_regions_correlation_above_point98': all(r['normalized_correlation'] > .98 for r in sync['probes']),
        'actual_AV_offset_with_codec_PTS_under20ms': all(abs(r['effective_audio_late_seconds']) <= .02 for r in sync['probes']),
        'no_audio_clock_drift_over20ms': max(r['decoded_PCM_lag_samples'] for r in sync['probes']) - min(r['decoded_PCM_lag_samples'] for r in sync['probes']) <= .02 * SR,
        'codec_unavailable_head_is_only_below_minus70dBFS': sync['initial_codec_unavailable_reference_peak_dbFS'] < -70,
        'original_audio_EOF_preserved_through_codec_tail': sync['full_reference_EOF_covered'],
        'original_MP4_PCM_sourceZIP_status_unchanged': before == protected(),
    }
    report = {'status': 'PASS_TECHNICAL_AWAITING_VISUAL_REVIEW' if all(checks.values()) else 'FAIL',
              'revision': 12, 'output_file': relative(file), 'output_sha256': sha(file),
              'output_bytes': file.stat().st_size, 'original_video_sha256': SOURCE_SHA,
              'PCM_source_sha256': PCM_SHA, 'frames': decoded_frames, 'fps': 30,
              'video_content_duration_seconds': content_duration,
              'ASF_container_duration_seconds': container_duration,
              'ASF_container_overhead_seconds': container_duration - content_duration,
              'timeline_sha256': sha(ROOT / 'timeline.json'), 'metadata': meta,
              'audio_sync': sync, 'visual_samples': records,
              'visual_review': {'status': 'PENDING'}, 'windows10_runtime_verified': False,
              'runtime_caveat': 'Local codec/structure/decode/sample checks do not prove playback on the user Windows10 Windows Media Player installation.',
              'reproduction_command_argv': [relative(x) if isinstance(x, Path) else x for x in command()],
              'helper_file': relative(Path(__file__)), 'helper_sha256': sha(Path(__file__)),
              'protected_before_after_sha256': before, 'checks': checks,
              'checks_passed': sum(checks.values()), 'checks_total': len(checks),
              'source_audio_processing': 'Original PCM mix encoded to WMA2 only. No TTS, volume, pitch, tempo, BGM edit, seek or cut retiming.',
              'timing_note': 'ASF millisecond PTS, encoder priming and tail padding are reported separately from the exact9724/30 video content clock. No metadata duration is presented as sample-exact PCM preservation.'}
    save(REPORT, report)
    print(json.dumps({'status': report['status'], 'checks': [report['checks_passed'], report['checks_total']], 'report': str(REPORT)}))
    assert all(checks.values()), checks


def finalize():
    report = json.loads(REPORT.read_text())
    assert report['status'] == 'PASS_TECHNICAL_AWAITING_VISUAL_REVIEW'
    assert all(report['checks'].values()) and report['visual_review']['status'] == 'PASS'
    assert sha(PARTIAL) == report['output_sha256'] and protected() == report['protected_before_after_sha256']
    assert not FINAL.exists(), 'Never replace an existing completed compatibility output silently'
    os.replace(PARTIAL, FINAL)
    report.update(status='PASS_WITH_WINDOWS_RUNTIME_CAVEAT', output_file=relative(FINAL),
                  output_sha256=sha(FINAL), completed_output_renamed_from_partial=True)
    save(REPORT, report)
    print(json.dumps({'status': report['status'], 'file': str(FINAL), 'sha256': report['output_sha256']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate-existing', action='store_true')
    parser.add_argument('--finalize', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.finalize:
        finalize()
        return
    if not args.validate_existing:
        assert sha(SOURCE) == SOURCE_SHA and sha(PCM) == PCM_SHA
        run(command())
    validate()


if __name__ == '__main__':
    main()
