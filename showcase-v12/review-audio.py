#!/usr/bin/env python3
"""Read-only independent PCM/tempo/music review; optionally review encoded AAC.

Only JSON receipts are written. This script never produces speech or rewrites
media. Full speech recognition and subjective tone acceptance are separate.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import subprocess
import wave

import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / 'out/showcase-v12'
SR = 48000
SONG_SHA = '285aafebdbb4879d1678dd8ae520fb1283c604c6b1756cc4c6e964c6fc55e7c2'


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def pcmsha(a):
    return hashlib.sha256(a.astype('<i2', copy=False).tobytes()).hexdigest()


def load(p):
    return json.loads(Path(p).read_text())


def save(p, value):
    Path(p).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                 allow_nan=False) + '\n')


def local(p):
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def read(p, channels):
    with wave.open(str(p)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getcomptype()) == (SR, channels, 2, 'NONE'), str(p)
        return np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').copy().reshape(-1, channels)


def run(args, binary=False):
    return subprocess.run([str(x) for x in args], check=True,
                          capture_output=True, text=not binary)


def level(p):
    result = run(['ffmpeg', '-hide_banner', '-nostats', '-i', p, '-af',
                  'loudnorm=I=-19.5:TP=-1:LRA=7:print_format=json', '-f', 'null', '-'])
    j = json.loads(re.findall(r'\{\s*"input_i".*?\}', result.stderr, re.S)[-1])
    return {k: float(j[k]) for k in ['input_i', 'input_tp', 'input_lra', 'input_thresh']}


def db(x):
    return 20 * np.log10(np.maximum(x, 1e-15))


def rms100(a):
    n = len(a) // 4800
    return np.sqrt(np.mean((a[:n * 4800].astype(np.float64) / 32768).reshape(n, -1) ** 2, axis=1))


def expected_music_chunk(song, start, end, total):
    """Index each original-song sample independently of the mixer implementation."""
    intro, period, overlap = 39 * SR, round(128 * 60 / 113 * SR), round(4 * 60 / 113 * SR)
    idx = np.arange(start, end)
    relative = idx - intro
    phase_index = np.maximum(relative, 0) % period
    cycle = np.maximum(relative, 0) // period
    source_index = np.where(idx < intro, idx, intro + phase_index)
    data = song[source_index].astype(np.float64)
    for cyc in np.unique(cycle[(idx >= intro) & (cycle > 0) & (phase_index < overlap)]):
        offset = intro + int(cyc) * period
        n = min(overlap, total - offset)
        mask = (idx >= offset) & (idx < offset + n)
        j = idx[mask] - offset
        phase = np.linspace(0, math.pi / 2, n)[j]
        data[mask] = song[intro + period + j].astype(np.float64) * np.cos(phase)[:, None] + song[intro + j].astype(np.float64) * np.sin(phase)[:, None]
    for n, first in [(min(total, 2 * SR), True), (min(total, 4 * SR), False)]:
        offset = 0 if first else total - n
        mask = (idx >= offset) & (idx < offset + n)
        j = idx[mask] - offset
        phase = np.linspace(0, math.pi, n)[j]
        factor = .5 - .5 * np.cos(phase) if first else .5 + .5 * np.cos(phase)
        data[mask] *= factor[:, None]
    # Preserve the approved total gain without clipping a float overlap before
    # it reaches the actual music level. This is already the gained base stem.
    return np.rint(data * .125).astype('<i2')


def yin_region(pcm, rate=SR):
    """Coarse local F0 evidence, not a formant or listening-quality test."""
    x = pcm.astype(np.float64).reshape(-1)[::6] / 32768
    fs = rate / 6
    frame, hop = 480, 120
    low, high = int(fs / 450), int(fs / 85)
    values = []
    for s in range(0, len(x) - frame - high, hop):
        a = x[s:s + frame + high]
        if np.sqrt(np.mean(a[:frame] ** 2)) < .012:
            continue
        a = a - np.mean(a)
        differences = np.zeros(high + 1)
        for tau in range(1, high + 1):
            differences[tau] = np.sum((a[:frame] - a[tau:tau + frame]) ** 2)
        cmnd = np.ones(high + 1)
        cmnd[1:] = differences[1:] * np.arange(1, high + 1) / np.maximum(np.cumsum(differences[1:]), 1e-20)
        candidates = [tau for tau in range(low, high) if cmnd[tau] < .15 and cmnd[tau] <= cmnd[tau - 1] and cmnd[tau] < cmnd[tau + 1]]
        if not candidates:
            continue
        tau = candidates[0]
        denom = cmnd[tau - 1] - 2 * cmnd[tau] + cmnd[tau + 1]
        offset = .5 * (cmnd[tau - 1] - cmnd[tau + 1]) / denom if abs(denom) > 1e-12 else 0
        values.append(fs / (tau + offset))
    return {'voiced_frames': len(values), 'median_Hz': float(np.median(values)) if values else None}


def f0_comparisons(original, fast):
    rows = []
    for fraction in [.15, .50, .85]:
        center = len(original) / SR * fraction
        a, b = max(0, center - 3), min(len(original) / SR, center + 3)
        src = yin_region(original[round(a * SR):round(b * SR)])
        dst = yin_region(fast[round(a / 1.15 * SR):round(b / 1.15 * SR)])
        cents = 1200 * math.log2(dst['median_Hz'] / src['median_Hz']) if src['median_Hz'] and dst['median_Hz'] else None
        rows.append({'source_seconds': [a, b], 'fast_seconds': [a / 1.15, b / 1.15],
                     'source': src, 'fast': dst, 'median_delta_cents': cents})
    return rows


def pcm_review():
    receipt_path = OUT / 'audio-validation.json'
    receipt = load(receipt_path)
    timeline = load(ROOT / 'timeline.json')
    placement = load(ROOT / 'narration/placement-manifest.json')
    descriptor = load(ROOT / 'narration/two-part-sources.json')
    total = timeline['frames'] * 1600
    fast = read(local(descriptor['fast_master']['path']), 1)
    original = read(local(descriptor['composite_master']['path']), 1)
    part_arrays = [read(local(p['master']), 1) for p in descriptor['parts']]
    raw, voice, loop, mixed = [read(OUT / n, c) for n, c in [('narration-raw.wav', 1), ('narration.wav', 1), ('bgm-loop.wav', 2), ('audio.wav', 2)]]
    base = read(OUT / 'audio-audit/music-base.wav', 2)
    music = read(OUT / 'audio-audit/music-final.wav', 2)
    expected = np.zeros((total, 1), dtype='<i2')
    occupied = np.zeros(total, dtype=bool)
    source_cursor = 0
    source_gaps = []
    for piece in placement['retained_pieces']:
        a, b, x, y = [piece[k] for k in ['source_start_sample', 'source_end_sample', 'destination_start_sample', 'destination_end_sample']]
        assert 0 <= a < b <= len(fast) and source_cursor <= a and 0 <= x < y <= total and b - a == y - x
        if a > source_cursor:
            source_gaps.append([source_cursor, a])
        assert not np.any(occupied[x:y]) and pcmsha(fast[a:b]) == piece['pcm_sha256']
        expected[x:y] = fast[a:b]
        occupied[x:y] = True
        source_cursor = b
    if source_cursor < len(fast):
        source_gaps.append([source_cursor, len(fast)])
    removals = placement.get('quiet_removals', [])
    removal_spans = [[p['source_start_sample'], p['source_end_sample']] for p in removals]
    quiet_proofs = []
    for a, b in removal_spans:
        x = fast[a:b].astype(np.float64) / 32768
        windows = [float(np.sqrt(np.mean(x[s:s + 480] ** 2))) for s in range(0, len(x), 480)]
        quiet_proofs.append({'source_start_sample': a, 'source_end_sample': b,
                             'maximum10ms_RMS_dbFS': float(db(max(windows, default=0)))})
    protected_ok = True
    for u in placement['utterances']:
        a, b, x, y = [u[k] for k in ['source_protected_start_sample', 'source_protected_end_sample', 'destination_speech_start_sample', 'destination_speech_end_sample']]
        protected_ok &= bool(np.array_equal(fast[a:b], raw[x:y]))
    gain = float(receipt['constant_voice_gain_db'])
    factor = 10 ** (gain / 20)
    voice_error = max_error = clipping = 0
    integer_sum = True
    music_base_error = 0
    music_phase_floor_violations = 0
    for start in range(0, total, 480000):
        end = min(start + 480000, total)
        ideal = np.rint(raw[start:end].astype(np.float64) * factor).astype(np.int64)
        err = voice[start:end].astype(np.int64) - ideal
        voice_error += int(np.count_nonzero(err))
        max_error = max(max_error, int(np.max(np.abs(err))))
        clipping += int(np.count_nonzero((ideal < -32768) | (ideal > 32767)))
        integer_sum &= bool(np.array_equal(mixed[start:end].astype(np.int32), voice[start:end].astype(np.int32) + music[start:end].astype(np.int32)))
        music_base_error = max(music_base_error, int(np.max(np.abs(base[start:end].astype(np.int32) - loop[start:end].astype(np.int32)))))
        dry, duck = base[start:end].astype(np.int32), music[start:end].astype(np.int32)
        nontrivial = np.abs(dry) > 4
        bad = (np.sign(dry[nontrivial]) != np.sign(duck[nontrivial])) | (np.abs(duck[nontrivial]) > np.abs(dry[nontrivial]) + 1) | (np.abs(duck[nontrivial]) < .4 * np.abs(dry[nontrivial]) - 2)
        music_phase_floor_violations += int(np.count_nonzero(bad))
    song_path = ROOT / load(ROOT / 'narration/ko.json')['bgm']
    song = read(OUT / 'audio-audit/bgm-original.wav', 2)
    loop_difference = 0
    for start in range(0, total, 480000):
        end = min(total, start + 480000)
        loop_difference += int(np.count_nonzero(expected_music_chunk(song, start, end, total) != loop[start:end]))
    title_ranges, card_ranges = [], []
    for entry in timeline['entries']:
        interval = [entry['start_frame'] * 1600, entry['end_frame'] * 1600]
        if entry['kind'] == 'title':
            title_ranges.append(interval)
        if entry['kind'] == 'silent':
            card_ranges.append(interval)
    br, mr, vr = rms100(base), rms100(music), rms100(voice)
    times = np.arange(len(mr)) / 10
    core = (times >= 2.1) & (times < total / SR - 4.1)
    active = core & (db(vr) > -32)
    ratios = np.divide(mr, br, out=np.ones_like(mr), where=br > 1e-9)
    voice_level, mix_level = level(OUT / 'narration.wav'), level(OUT / 'audio.wav')
    pitch = f0_comparisons(original, fast)
    f0_ok = all(p['median_delta_cents'] is not None and abs(p['median_delta_cents']) < 100 and min(p['source']['voiced_frames'], p['fast']['voiced_frames']) >= 10 for p in pitch)
    bindings_current = all(sha(local(p)) == digest for p, digest in receipt['input_bindings'].items())
    files_current = all(sha(OUT / p) == d['sha256'] for p, d in receipt['files'].items())
    checks = {
        'current_audio_receipt_PASS_and_all_bindings_current': receipt['status'].startswith('PASS') and bindings_current and files_current,
        'two_raw_parts_exact_ordered_concat': len(part_arrays) == 2 and np.array_equal(original, np.concatenate(part_arrays)),
        'actual_global_fast_master_matches_descriptor': sha(local(descriptor['fast_master']['path'])) == descriptor['fast_master']['sha256'] and pcmsha(fast) == descriptor['fast_master']['pcm_sha256'],
        'actual_tempo_sample_ratio_within5ms': abs(len(fast) - len(original) / 1.15) <= .005 * SR,
        'three_region_F0_no_pitch_shift_coarse_evidence': f0_ok,
        'all_retained_master_ranges_and_zero_gaps_PCM_exact': np.array_equal(raw, expected),
        'omitted_source_ranges_exact_explicit_quiet_removals': source_gaps == removal_spans,
        'only_explicit_quiet_removal_wave_windows': all(p['maximum10ms_RMS_dbFS'] <= -48 for p in quiet_proofs),
        '68_complete_protected_utterance_ranges_exact': len(placement['utterances']) == 68 and protected_ok,
        'all_WAV_frame_locked_48k_duration_at_most330': all(len(a) == total for a in [raw, voice, loop, mixed, base, music]) and total / SR <= 330,
        '12_titles_each60frames_and_voice_zero': len(title_ranges) == 12 and all(b - a == 96000 and not np.any(voice[a:b]) for a, b in title_ranges),
        'last_card120frames_voice_literal_zero': len(card_ranges) == 1 and card_ranges[0][1] == total and card_ranges[0][1] - card_ranges[0][0] == 192000 and not np.any(voice[card_ranges[0][0]:]),
        'all_voice_samples_exact_single_gain': voice_error == max_error == clipping == 0,
        'voice_loudness_minus19_5_within_quarterLU': abs(voice_level['input_i'] + 19.5) <= .25,
        'original_song_identity_and_independent_loop_PCM_exact': sha(song_path) == SONG_SHA and loop_difference == 0,
        'music_base_exact_prequantized_point125_gain_loop': music_base_error == 0,
        'duck_per_sample_same_sign_and_point4_to1_envelope': music_phase_floor_violations == 0,
        'duck_dry_floor_at_least_minus8_1dB': float(np.min(db(ratios)[core])) >= -8.1,
        'continuous_BGM_no100ms_zero_between_fades': not np.any(mr[core] == 0),
        'mix_exact_voice_plus_music': integer_sum,
        'no_voice_or_mix_clipping_and_truepeaks_below0': clipping == 0 and np.max(np.abs(mixed.astype(np.int32))) < 32767 and voice_level['input_tp'] < 0 and mix_level['input_tp'] < 0,
    }
    gap_p05 = float(np.percentile((db(vr) - db(mr))[active], 5))
    advisory = {'speech_at_least6dB_above_music_in95pct_active_windows': {
        'pass': gap_p05 >= 6, 'target_db': 6, 'actual_db': gap_p05,
        'shortfall_db': max(0., 6 - gap_p05),
        'policy': 'Independent measured advisory; fixed source-song/gain/duck and voice level are preserved. The6dB target has not been lowered or reclassified as passed.'}}
    return {
        'revision': 12, 'status': ('PASS_INDEPENDENT_AUDIO_PCM' if all(x['pass'] for x in advisory.values()) else 'PASS_WITH_BALANCE_CAVEAT') if all(checks.values()) else 'FAIL',
        'source_identity_sha256': descriptor['source_identity_sha256'],
        'timeline_sha256': sha(ROOT / 'timeline.json'), 'audio_validation_sha256': sha(receipt_path),
        'narration_sha256': sha(OUT / 'narration.wav'), 'audio_sha256': sha(OUT / 'audio.wav'),
        'speech_tempo': 1.15, 'pitch_cents': 0, 'duration_seconds': total / SR,
        'frames': timeline['frames'], 'samples': total,
        'raw_reconstructed_PCM_sha256': pcmsha(expected),
        'voice_single_gain_mismatch_samples': voice_error, 'maximum_absolute_sample_error': max_error,
        'loop_independent_reconstruction_mismatch_samples': loop_difference,
        'music_base_maximum_quantization_error': music_base_error,
        'music_gain_quantization_policy': 'Reconstructed float original-song crossfades/fades, applied total0.125 gain, then one int16 quantization. No intermediate full-scale clipping or second0.125 gain.',
        'music_sample_phase_or_dry_floor_violations': music_phase_floor_violations,
        'constant_voice_gain_db': gain, 'source_quiet_removals': quiet_proofs,
        'F0_comparisons': pitch, 'F0_tolerance_cents': 100,
        'F0_scope': 'Coarse same-content YIN median evidence to distinguish tempo from a sample-rate pitch change. Not a guarantee of unchanged formants, exact F0 or perceived tone.',
        'voice_measurement': voice_level, 'mix_measurement': mix_level,
        'minimum_duck_db': float(np.min(db(ratios)[core])),
        'speech_minus_music_db_P05': float(np.percentile((db(vr) - db(mr))[active], 5)),
        'checks': {k: bool(v) for k, v in checks.items()},
        'core_checks': {k: bool(v) for k, v in checks.items()},
        'advisory_balance_checks': advisory,
        'checks_passed': sum(bool(v) for v in checks.values()), 'checks_total': len(checks),
        'scope': 'Independent actual PCM/gain/tempo/F0/music-envelope calculations. Complete ASR, human listening and encoded playback are separate.',
        'input_bindings': {'review-audio.py': sha(Path(__file__)),
                           'narration/placement-manifest.json': sha(ROOT / 'narration/placement-manifest.json'),
                           'narration/two-part-sources.json': sha(ROOT / 'narration/two-part-sources.json'),
                           'timeline.json': sha(ROOT / 'timeline.json')},
    }


def streamhash(p, stream):
    return run(['ffmpeg', '-v', 'error', '-i', p, '-map', '0:' + stream,
                '-c', 'copy', '-f', 'hash', '-hash', 'sha256', '-']).stdout.strip()


def decode(p):
    result = run(['ffmpeg', '-v', 'error', '-xerror', '-err_detect', 'explode',
                  '-i', p, '-map', '0:a:0', '-ar', str(SR), '-ac', '2',
                  '-c:a', 'pcm_s16le', '-f', 's16le', '-'], binary=True)
    return np.frombuffer(result.stdout, dtype='<i2').reshape(-1, 2)


def encoded_review():
    mux_path = OUT / 'mux-validation.json'
    mux = load(mux_path)
    timeline = load(ROOT / 'timeline.json')
    placement = load(ROOT / 'narration/placement-manifest.json')
    final = OUT / 'RD_Process_AI_Fast_Track_Showcase_Revision12.mp4'
    reference = OUT / 'audio-audit/mix-aac.m4a'
    before = sha(final)
    actual, encoded_reference = decode(final), decode(reference)
    pcm = read(OUT / 'audio.wav', 2)
    raw = read(OUT / 'narration-raw.wav', 1)
    regions = []
    section_ids = list(dict.fromkeys(u['section_id'] for u in placement['utterances']))
    for sid in section_ids:
        lines = [u for u in placement['utterances'] if u['section_id'] == sid]
        a, b = min(u['destination_speech_start_sample'] for u in lines), max(u['destination_speech_end_sample'] for u in lines)
        n = min(24000, b - a)
        starts = range(a, max(a + 1, b - n + 1), 4800)
        start = max(starts, key=lambda s: float(np.mean(raw[s:s + n].astype(np.float64) ** 2)))
        center = pcm[start:start + n].astype(np.float64).mean(axis=1)
        center -= center.mean()
        scores = []
        for lag in range(-64, 65):
            x = start + lag
            if x < 0 or x + n > len(actual):
                continue
            candidate = actual[x:x + n].astype(np.float64).mean(axis=1)
            candidate -= candidate.mean()
            denom = np.linalg.norm(center) * np.linalg.norm(candidate)
            scores.append((float(np.dot(center, candidate) / max(denom, 1e-20)), lag))
        score, lag = max(scores)
        regions.append({'section_id': sid, 'start_sample': start, 'end_sample': start + n,
                        'best_lag_samples': lag, 'normalized_correlation': score})
    meta = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', final]).stdout)
    a = next(s for s in meta['streams'] if s['codec_type'] == 'audio')
    packet = streamhash(final, 'a:0')
    reference_packet = streamhash(reference, 'a:0')
    duration = timeline['frames'] / 30
    checks = {
        'current_mux_receipt_PASS_and_MP4_sha_matches': mux['status'].startswith('PASS') and mux['final_video_sha256'] == before,
        'AAC_packets_exact_single_encoded_reference': packet == reference_packet == mux['audio_stream_sha256'],
        'full_AAC_strict_decode_and_reference_PCM_exact': np.array_equal(actual, encoded_reference),
        'AAC_clock_48k_stereo_and_zero_start': int(a['sample_rate']) == SR and a['channels'] == 2 and abs(float(a.get('start_time', 0))) <= 1 / SR,
        'AAC_duration_matches_actual_timeline_within1ms': abs(float(a['duration']) - duration) <= .001,
        'decoder_tail_padding_at_most_one_AAC_frame': 0 <= len(actual) - len(pcm) <= 1024,
        'all14_blocks_actual_encoded_zero_sample_lag': len(regions) == 14 and all(r['best_lag_samples'] == 0 for r in regions),
        'all14_blocks_AAC_PCM_correlation_above_point98': all(r['normalized_correlation'] > .98 for r in regions),
        'MP4_and_PCM_inputs_unchanged_during_review': sha(final) == before and sha(OUT / 'audio.wav') == mux['pcm_mix_sha256'],
    }
    caveats = mux.get('advisory_balance_checks', {})
    balance_ok = all(item['pass'] for item in caveats.values())
    return {'revision': 12, 'status': ('PASS_ENCODED_AUDIO' if balance_ok else 'PASS_WITH_BALANCE_CAVEAT') if all(checks.values()) else 'FAIL',
            'final_video_sha256': before, 'timeline_sha256': sha(ROOT / 'timeline.json'),
            'source_identity_sha256': mux['source_identity_sha256'],
            'mux_validation_sha256': sha(mux_path), 'pcm_mix_sha256': sha(OUT / 'audio.wav'),
            'audio_stream_sha256': packet, 'AAC_reference_sha256': sha(reference),
            'decoded_samples': len(actual), 'expected_PCM_samples': len(pcm),
            'decoded_tail_padding_samples': len(actual) - len(pcm),
            'sample_rate': SR, 'duration_seconds': duration, 'regions': regions,
            'checks': checks, 'checks_passed': sum(checks.values()), 'checks_total': len(checks),
            'advisory_balance_checks': caveats,
            'scope': 'Actual final AAC packet identity, full strict audio decode and zero-lag alignment to the PCM mix in14 blocks. No new TTS, speech recognition or subjective listening.',
            'review_script_sha256': sha(Path(__file__))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--encoded', action='store_true')
    args = parser.parse_args()
    destination = OUT / ('encoded-audio-validation.json' if args.encoded else 'independent-audio-validation.json')
    try:
        report = encoded_review() if args.encoded else pcm_review()
    except Exception as exc:
        report = {'revision': 12, 'status': 'FAIL', 'error': f'{type(exc).__name__}: {exc}',
                  'scope': 'Read-only review; no media was changed.'}
    save(destination, report)
    print(json.dumps({'status': report['status'], 'checks': [report.get('checks_passed'), report.get('checks_total')],
                      'report': str(destination)}, ensure_ascii=False))
    return 0 if report['status'].startswith('PASS') else 1


if __name__ == '__main__':
    raise SystemExit(main())
