#!/usr/bin/env python3
"""Independent Revision11 PCM/gain and optional copied-video identity review.

Reads frozen inputs only; writes its own JSON receipt. It never generates,
normalizes, filters, resamples, splices, or overwrites any media.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import wave

import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / 'out/showcase-v11'
VISUAL = ROOT / 'visual-source-v10'
RATE = 48000
SAMPLES = 15120000
BASE_RAW_SHA = '6ffd0cedda626853c222e5c960ac8df862e764cf7e62845075fdc7c6f1663620'
BASE_RAW_PCM_SHA = '8194f0e68353a3b5a3e8a51a9b743bfd9cb9d7a5247ae2d68a52128b75167ae1'
BASE_MUSIC_SHA = 'f51dc5750fc27dabb13f73e9c96945fee270e13f3bbb4106555b07c021941bfb'
BASE_MUSIC_PCM_SHA = '4666d41861a90af4d4d16202fd4ec219143f17c3ef39d3ff3ac4eae2138d730a'
BASE_TIMELINE_SHA = '8beda6d4a6871df3542f86a1aacf7d4d6912caed99923a90b3725796f6958318'
BASE_SPEC_SHA = '0f6a3caf04d1d82a728f476b21c166fa225f2cd113c57cd27e92185378d19345'
BASE_KO_SHA = 'af520ba9516474fbf10a46df3f254b0cf16d1795d4158e8952752f7c9d2d64ca'
BASE_PLAN_SHA = 'ff38348f4f94a046381dfc29d357e8a6ebfb14224d4ab011e1706725cbda7abf'
BASE_SILENT_SHA = '2217673d0cef3bbaa1c8cc9ec2bd3b0c02124d00ba2baed43039ce7772f2b45f'
BASE_VIDEO_STREAM_SHA = 'SHA256=29cf7420deb9e4a82f398e4439198840f3b0adee4ee49ab16fc2f1298748f294'
SOURCE_ID = '92c31c5917cbb6a5c7d8f7f998ac005bdd43bfb1e69e79183333c5dfcca5e3c2'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def pcmsha(data):
    return hashlib.sha256(data.astype('<i2', copy=False).tobytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def relative(path):
    return str(Path(path).relative_to(ROOT)) if Path(path).is_relative_to(ROOT) else '../' + str(Path(path).relative_to(ROOT.parent))


def binding(paths):
    return {relative(p): sha(p) for p in paths}


def read16(path, channels):
    with wave.open(str(path)) as w:
        meta = {'sample_rate': w.getframerate(), 'channels': w.getnchannels(),
                'sample_width': w.getsampwidth(), 'samples': w.getnframes(),
                'compression': w.getcomptype()}
        assert (meta['sample_rate'], meta['channels'], meta['sample_width'], meta['compression']) == (RATE, channels, 2, 'NONE'), (path, meta)
        data = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').copy().reshape(-1, channels)
    return data, meta


def db(value):
    return float(20 * math.log10(max(float(value), 1e-15)))


def level(path):
    args = ['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-af',
            'loudnorm=I=-19.3:TP=-1:LRA=7:print_format=json', '-f', 'null', '-']
    result = subprocess.run(args, capture_output=True, text=True, check=True)
    rows = re.findall(r'\{\s*"input_i".*?\}', result.stderr, re.S)
    assert rows, 'FFmpeg input loudness measurement missing'
    measured = json.loads(rows[-1])
    return {key: float(measured[key]) for key in ['input_i', 'input_tp', 'input_lra', 'input_thresh']}


def rms100(data):
    count = len(data) // 4800
    return np.sqrt(np.mean((data[:count * 4800].astype(np.float64) / 32768).reshape(count, -1) ** 2, axis=1))


def raw_from_approved_plan(plan):
    virtual = np.zeros((SAMPLES, 1), dtype='<i2')
    occupied = np.zeros(SAMPLES, dtype=bool)
    sources = {}
    paths = []
    for part in plan['source_parts']:
        path = VISUAL / part['master']
        assert sha(path) == part['master_sha256'], 'Original source identity changed'
        sources[part['part_id']] = read16(path, 1)[0]
        paths.append(path)
    pieces = [piece for cut in plan['placements'] for piece in cut.get('pieces', [])] + plan['audio_groups']
    proof = []
    for piece in sorted(pieces, key=lambda p: p['destination_start_sample']):
        a, b = piece['source_local_start_sample'], piece['source_local_end_sample']
        x, y = piece['destination_start_sample'], piece['destination_end_sample']
        source = sources[piece['source_part_id']][a:b]
        assert 0 <= x < y <= SAMPLES and b - a == y - x == len(source)
        assert not np.any(occupied[x:y]), 'Approved pieces overlap'
        assert pcmsha(source) == piece['pcm_sha256'], 'Retained source piece changed'
        virtual[x:y] = source
        occupied[x:y] = True
        proof.append({'source_part_id': piece['source_part_id'], 'source_start_sample': a,
                      'source_end_sample': b, 'destination_start_sample': x,
                      'destination_end_sample': y, 'pcm_sha256': piece['pcm_sha256']})
    assert len(pieces) == 77 and len(plan['placements']) == 68
    return virtual, proof, paths


def review_audio():
    audio_receipt_path = OUT / 'audio-validation.json'
    receipt = load(audio_receipt_path)
    auth_path = ROOT / 'authorization.json'
    auth = load(auth_path)
    plan_path = VISUAL / 'narration/retime/approved-plan.json'
    plan = load(plan_path)
    timeline_path = VISUAL / 'timeline.json'
    timeline = load(timeline_path)
    names = ['narration-raw.wav', 'narration.wav', 'bgm-loop.wav', 'audio.wav']
    arrays, files = {}, {}
    paths = [ROOT / 'review-audio.py', auth_path, ROOT / 'baseline-provenance.json',
             audio_receipt_path, timeline_path, VISUAL / 'spec.json', VISUAL / 'narration/ko.json', plan_path]
    for name in names:
        path = OUT / name
        arrays[name], metadata = read16(path, 1 if name.startswith('narration') else 2)
        files[name] = {**metadata, 'sha256': sha(path), 'pcm_sha256': pcmsha(arrays[name])}
        paths.append(path)
    raw, voice, music, mixed = [arrays[name] for name in names]
    virtual, pieces, source_paths = raw_from_approved_plan(plan)
    paths.extend(source_paths)
    gain_db = float(receipt['constant_voice_gain_db'])
    factor = 10 ** (gain_db / 20)
    differences, maximum_error, clipping = 0, 0, 0
    integer_mix_exact = True
    for start in range(0, SAMPLES, 480000):
        stop = min(SAMPLES, start + 480000)
        expected = np.rint(raw[start:stop].astype(np.float64) * factor).astype(np.int64)
        actual = voice[start:stop].astype(np.int64)
        error = actual - expected
        differences += int(np.count_nonzero(error))
        maximum_error = max(maximum_error, int(np.max(np.abs(error))))
        clipping += int(np.count_nonzero((expected < -32768) | (expected > 32767)))
        integer_mix_exact &= bool(np.array_equal(mixed[start:stop].astype(np.int32), actual.astype(np.int32) + music[start:stop].astype(np.int32)))
    music_source_path = VISUAL / 'assets/bgm/revision9-approved-music.wav'
    music_source, _ = read16(music_source_path, 2)
    paths.append(music_source_path)
    voice_level, mix_level = level(OUT / 'narration.wav'), level(OUT / 'audio.wav')
    music_rms = rms100(music)
    body = music_rms[math.ceil(39.233333333333334 * 10):math.floor(296.3333333333333 * 10)]
    body_quiet = body < 10 ** (-60 / 20)
    longest = current = 0
    for quiet in body_quiet:
        current = current + 1 if quiet else 0
        longest = max(longest, current)
    sample_peak = int(np.max(np.abs(mixed.astype(np.int32))))
    expected_receipt_files = all(receipt.get('files', {}).get(name, {}).get('sha256') == files[name]['sha256'] for name in names)
    checks = {
        'authorization_pitch0_rate1_no_other_processing': auth['pitch_shift_cents'] == 0 and auth['speech_tempo'] == 1 and auth['pitch_or_time_processor_allowed'] is False,
        'timeline_byte_exact_revision10_315s9450frames': sha(timeline_path) == BASE_TIMELINE_SHA and timeline['frames'] == 9450 and timeline['duration'] == 315 and len(timeline['entries']) == 69,
        'spoken68_and_design_source_byte_exact': sha(VISUAL / 'spec.json') == BASE_SPEC_SHA and sha(VISUAL / 'narration/ko.json') == BASE_KO_SHA and len(plan['placements']) == 68,
        'all4_WAV_315s48k_signed16': all(item['samples'] == SAMPLES for item in files.values()),
        'raw_file_and_PCM_exact_revision10': files['narration-raw.wav']['sha256'] == BASE_RAW_SHA and files['narration-raw.wav']['pcm_sha256'] == BASE_RAW_PCM_SHA,
        'all77_retained_source_pieces_and_zero_gaps_exact': sha(plan_path) == BASE_PLAN_SHA and np.array_equal(raw, virtual),
        'processed_voice_exact_single_constant_gain_rounding': differences == 0 and maximum_error == 0 and clipping == 0,
        'gain_factor_metadata_matches_gain_db': abs(float(receipt.get('gain_factor', factor)) - factor) <= 1e-12 * factor,
        'pitch0_tempo1_source_identity_receipt': receipt['pitch_cents'] == 0 and receipt.get('speech_tempo', receipt.get('tempo')) == 1 and receipt['source_identity_sha256'] == SOURCE_ID,
        'voice_level_matches_previous_minus19_3_LUFS': abs(voice_level['input_i'] + 19.3) <= 0.2,
        'music315s_PCM_exact_revision10': pcmsha(music) == BASE_MUSIC_PCM_SHA,
        'music314_5s_prefix_exact_and_only0_5s_zero_tail': len(music_source) == 15096000 and np.array_equal(music[:len(music_source)], music_source) and not np.any(music[len(music_source):]),
        'mix_exact_integer_voice_plus_unchanged_music': integer_mix_exact,
        'no_voice_or_mix_sample_clipping': clipping == 0 and sample_peak < 32767 and int(np.max(np.abs(voice.astype(np.int32)))) < 32767,
        'independent_mix_true_peak_below0': mix_level['input_tp'] < 0,
        'unchanged_body_music_no100ms_drop_below_minus60': not np.any(body_quiet),
        'raw_and_processed_final4s_card_literal_zero': not np.any(raw[311 * RATE:]) and not np.any(voice[311 * RATE:]),
        'actual_audio_receipt_all4_files_current': receipt['status'] == 'PASS' and expected_receipt_files and receipt['timeline_sha256'] == BASE_TIMELINE_SHA,
    }
    report = {
        'revision': 11, 'status': 'PASS_INDEPENDENT_AUDIO_PCM' if all(checks.values()) else 'FAIL',
        'scope': 'Independent complete PCM reconstruction, uniform-gain identity, locked music and integer mix. Video identity is a separate optional report. No new transcription, full playback or subjective listening is claimed.',
        'speech_tempo': 1, 'pitch_cents': 0, 'duration_seconds': 315, 'frames': 9450,
        'source_identity_sha256': SOURCE_ID, 'timeline_sha256': sha(timeline_path),
        'audio_sha256': files['audio.wav']['sha256'], 'narration_sha256': files['narration.wav']['sha256'],
        'raw_sha256': files['narration-raw.wav']['sha256'], 'bgm_sha256': files['bgm-loop.wav']['sha256'],
        'files': files, 'constant_voice_gain_db': gain_db, 'gain_factor': factor,
        'quantization_independently_evaluated': 'np.rint(raw_signed16.astype(float64) * 10**(gain_db/20)); signed16 output',
        'voice_changed_sample_count_vs_single_gain': differences, 'maximum_absolute_sample_error': maximum_error,
        'whole_sample_gain_identity_proves_no_additional_waveform_DSP': differences == 0,
        'independent_loudness_measurements': {'voice': voice_level, 'mix': mix_level, 'method': 'FFmpeg loudnorm input measurements to null; no media output'},
        'music_body_min100ms_RMS_dbFS': db(np.min(body)), 'music_body_median100ms_RMS_dbFS': db(np.median(body)),
        'music_body_below_minus60_count': int(np.count_nonzero(body_quiet)),
        'music_body_below_minus60_longest_seconds': longest / 10,
        'mix_sample_peak_dbFS': db(sample_peak / 32768), 'retained_source_piece_count': len(pieces),
        'retained_source_pieces': pieces, 'checks': {k: bool(v) for k, v in checks.items()},
        'checks_passed': sum(bool(v) for v in checks.values()), 'checks_total': len(checks),
        'input_bindings': binding(paths),
        'limitations': ['Sample-exact gain preserves the approved speech contents and boundaries; this is not a new linguistic or pronunciation review.', 'Natural voice preference and listening acceptance remain for the user.'],
    }
    return report


def video_stream_hash(path):
    result = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:v:0', '-c:v', 'copy', '-f', 'streamhash', '-hash', 'sha256', '-'], capture_output=True, text=True, check=True)
    match = re.search(r'SHA256=[0-9a-f]{64}', result.stdout)
    assert match, 'Copied video packet hash not available'
    return match.group(0)


def review_video():
    final = OUT / 'RD_Process_AI_Fast_Track_Showcase_Revision11.mp4'
    locked = ROOT / 'assets/video/locked-silent.mp4'
    timeline = VISUAL / 'timeline.json'
    probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(final)], capture_output=True, text=True, check=True).stdout)
    video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    audio = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    current_hash = video_stream_hash(final)
    locked_hash = video_stream_hash(locked)
    checks = {
        'timeline_byte_exact_revision10': sha(timeline) == BASE_TIMELINE_SHA,
        'locked_silent_file_byte_exact_revision10': sha(locked) == BASE_SILENT_SHA,
        'all_final_video_packets_exact_locked_revision10': current_hash == locked_hash == BASE_VIDEO_STREAM_SHA,
        'video315s9450frames1920x1080at30': int(video['nb_frames']) == 9450 and abs(float(video['duration']) - 315) < 1e-6 and video['width'] == 1920 and video['height'] == 1080 and video['avg_frame_rate'] == '30/1',
        'container315s_and_AAC48k_stereo': abs(float(probe['format']['duration']) - 315) < 1e-6 and audio['codec_name'] == 'aac' and int(audio['sample_rate']) == RATE and audio['channels'] == 2,
    }
    return {'revision': 11, 'status': 'PASS' if all(checks.values()) else 'FAIL',
            'scope': 'Independent container/stream metadata and exact copied-video packet identity. No full decode, rerender, playback or listening was repeated.',
            'final_video_sha256': sha(final), 'video_stream_sha256': current_hash,
            'locked_video_stream_sha256': locked_hash, 'timeline_sha256': sha(timeline),
            'duration_seconds': 315, 'frames': 9450, 'checks': checks,
            'checks_passed': sum(checks.values()), 'checks_total': len(checks),
            'input_bindings': binding([ROOT / 'review-audio.py', timeline, locked, final])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--video-only', action='store_true', help='Review final copied video identity after mux; skip PCM/loudness measurements.')
    args = parser.parse_args()
    output = OUT / ('independent-video-preservation.json' if args.video_only else 'independent-audio-validation.json')
    try:
        report = review_video() if args.video_only else review_audio()
    except Exception as exc:
        report = {'revision': 11, 'status': 'FAIL', 'scope': 'No media was modified by this review.',
                  'error': f'{type(exc).__name__}: {exc}'}
    save(output, report)
    print(json.dumps({'status': report['status'], 'checks_passed': report.get('checks_passed'),
                      'checks_total': report.get('checks_total'), 'report': str(output)}, ensure_ascii=False))
    return 0 if report['status'].startswith('PASS') else 1


if __name__ == '__main__':
    sys.exit(main())
