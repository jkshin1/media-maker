#!/usr/bin/env python3
"""Reproduce Revision12's two-part, global-tempo narration and music mix.

No service is called. The two authorized raw takes are concatenated, then one
atempo=1.15 pass is reproduced in the audit directory. Approved placement copies
that processed master without further tempo/pitch processing. Voice level uses
one constant gain; only the music is sidechain compressed.
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
RATE = 48000
SONG_SHA = '285aafebdbb4879d1678dd8ae520fb1283c604c6b1756cc4c6e964c6fc55e7c2'
MUSIC_POLICY = dict(bpm=113, intro_seconds=39, period_beats=128,
                    overlap_beats=4, fade_in_seconds=2, fade_out_seconds=4,
                    base_gain=.125, threshold=.018, ratio=4, attack_ms=45,
                    release_ms=650, wet_mix=.6, dry_floor=.4)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def pcmsha(a):
    return hashlib.sha256(a.astype('<i2', copy=False).tobytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False) + '\n')


def path_from(value):
    p = Path(value)
    return p if p.is_absolute() else ROOT / p


def portable(path):
    p = Path(path).resolve()
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return '../' + p.relative_to(ROOT.parent).as_posix()


def run(args):
    return subprocess.run([str(a) for a in args], check=True,
                          capture_output=True, text=True)


def read(path, channels):
    with wave.open(str(path)) as w:
        assert (w.getframerate(), w.getsampwidth(), w.getnchannels(), w.getcomptype()) == (RATE, 2, channels, 'NONE'), str(path)
        return np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').copy().reshape(-1, channels)


def write(path, a):
    a = np.asarray(a)
    assert a.ndim == 2 and np.max(np.abs(a.astype(np.int64)), initial=0) <= 32767
    with wave.open(str(path), 'wb') as w:
        w.setframerate(RATE)
        w.setsampwidth(2)
        w.setnchannels(a.shape[1])
        w.writeframes(a.astype('<i2').tobytes())


def measure(path, ffmpeg='ffmpeg'):
    r = run([ffmpeg, '-hide_banner', '-nostats', '-i', path, '-af',
             'loudnorm=I=-19.5:TP=-1:LRA=7:print_format=json', '-f', 'null', '-'])
    found = re.findall(r'\{\s*"input_i".*?\}', r.stderr, re.S)
    assert found, 'No FFmpeg loudness measurement'
    j = json.loads(found[-1])
    return {k: float(j[k]) for k in ['input_i', 'input_tp', 'input_lra', 'input_thresh']}


def db(x):
    return 20 * np.log10(np.maximum(x, 1e-15))


def rms100(a):
    count = len(a) // 4800
    return np.sqrt(np.mean((a[:count * 4800].astype(np.float64) / 32768).reshape(count, -1) ** 2, axis=1))


def build_music(original, total):
    """The Revision9 music recipe, with the final fade tied to this timeline."""
    assert original.shape[1] == 2
    intro = 39 * RATE
    period = round(128 * 60 / 113 * RATE)
    overlap = round(4 * 60 / 113 * RATE)
    assert len(original) >= intro + period + overlap
    music = np.zeros((total, 2), dtype=np.float64)
    music[:min(total, intro)] = original[:min(total, intro)]
    core = original[intro:intro + period + overlap].astype(np.float64)
    crossfades = []
    for offset in range(intro, total, period):
        n = min(len(core), total - offset)
        if offset == intro:
            music[offset:offset + n] = core[:n]
            continue
        nf = min(overlap, n)
        phase = np.linspace(0, math.pi / 2, nf)
        music[offset:offset + nf] = (music[offset:offset + nf] * np.cos(phase)[:, None]
                                          + core[:nf] * np.sin(phase)[:, None])
        if n > nf:
            music[offset + nf:offset + n] = core[nf:n]
        crossfades.append({'start_sample': offset, 'end_sample': offset + nf,
                          'start': offset / RATE, 'end': (offset + nf) / RATE})
    ni, no = min(total, 2 * RATE), min(total, 4 * RATE)
    music[:ni] *= (.5 - .5 * np.cos(np.linspace(0, math.pi, ni)))[:, None]
    music[-no:] *= (.5 + .5 * np.cos(np.linspace(0, math.pi, no)))[:, None]
    pre_gain_peak = float(np.max(np.abs(music)))
    pre_gain_outside = int(np.count_nonzero((music < -32768) | (music > 32767)))
    # Equal-power overlaps may exceed full scale before the selected0.125 gain.
    # Quantizing/clipping that intermediate first would unnecessarily distort
    # the overlap. Apply the same total gain in float, then quantize once.
    music *= MUSIC_POLICY['base_gain']
    assert np.max(np.abs(music)) < 32767, 'Music loop clips after its approved gain'
    return np.rint(music).astype('<i2'), {
        **MUSIC_POLICY, 'loop_source_samples': [intro, intro + period + overlap],
        'period_samples': period, 'overlap_samples': overlap,
        'crossfades': crossfades, 'source_speed_changed': False,
        'final_fade_start_sample': total - no, 'final_fade_end_sample': total,
        'gain_application': 'Floating-point loop and fades, then0.125 total gain, then one signed16 quantization; no intermediate int16 clipping.',
        'pre_gain_float_peak_in_int16_units': pre_gain_peak,
        'pre_gain_float_values_outside_int16': pre_gain_outside,
    }


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def reproduce_source(descriptor, audit, ffmpeg):
    parts = descriptor['parts']
    assert len(parts) == 2 and [len(p['cut_ids']) for p in parts] == [33, 35]
    assert len({cid for p in parts for cid in p['cut_ids']}) == 68
    buffers, paths, cursor = [], [], 0
    for p in parts:
        path = path_from(p['master'])
        data = read(path, 1)
        assert sha(path) == p['master_sha256'] and pcmsha(data) == p['master_pcm_sha256']
        assert len(data) == p['samples']
        if 'virtual_start_sample' in p:
            assert p['virtual_start_sample'] == cursor and p['virtual_end_sample'] == cursor + len(data)
        prompt = path_from(p['prompt_file'])
        assert sha(prompt) == p['prompt_sha256']
        assert p['generation_id'], 'Generation identity is required for each actual part'
        buffers.append(data)
        paths.extend([path, prompt])
        cursor += len(data)
    original = np.concatenate(buffers)
    expected_original = descriptor['composite_master']
    original_path = path_from(expected_original['path'])
    assert sha(original_path) == expected_original['sha256']
    assert pcmsha(original) == expected_original['pcm_sha256']
    assert np.array_equal(original, read(original_path, 1)) and len(original) == expected_original['samples']
    reproduced_original = audit / 'reproduced-complete-original.wav'
    write(reproduced_original, original)
    reproduced_fast = audit / 'reproduced-complete-tempo1.15.wav'
    command = [ffmpeg, '-y', '-v', 'error', '-i', reproduced_original,
               '-af', 'atempo=1.15', '-ar', str(RATE), '-ac', '1',
               '-c:a', 'pcm_s16le', reproduced_fast]
    run(command)
    fast_info = descriptor['fast_master']
    fast_path = path_from(fast_info['path'])
    fast = read(fast_path, 1)
    assert sha(fast_path) == fast_info['sha256'] and pcmsha(fast) == fast_info['pcm_sha256']
    assert len(fast) == fast_info['samples']
    assert np.array_equal(read(reproduced_fast, 1), fast), 'Global atempo reproduction differs'
    tempo_path = path_from(descriptor['tempo_provenance']['path'])
    assert sha(tempo_path) == descriptor['tempo_provenance']['sha256']
    tempo = load(tempo_path)
    assert tempo.get('speech_tempo_requested', tempo.get('speech_tempo', 1.15)) == 1.15
    assert tempo.get('pitch_cents', 0) == 0
    auth = descriptor['authorization']
    assert sha(path_from(auth['path'])) == auth['sha256']
    assert canonical_hash(descriptor['source_identity_payload']) == descriptor['source_identity_sha256']
    return original, fast, paths + [original_path, fast_path, tempo_path, path_from(auth['path'])], {
        'raw_parts': 2, 'generation_ids': [p['generation_id'] for p in parts],
        'source_samples': len(original), 'processed_samples': len(fast),
        'duration_ratio': len(original) / len(fast),
        'ideal_output_sample_difference': len(fast) - len(original) / 1.15,
        'reproduced_global_tempo_PCM_exact': True,
        'command': [str(x) if not isinstance(x, Path) else portable(x) for x in command],
        'extra_pitch_or_sample_rate_shift': False,
        'note': 'atempo uses WSOLA overlap; raw PCM bit identity is not claimed across tempo processing.',
    }


def assemble(placement, fast, total, timeline):
    raw = np.zeros((total, 1), dtype='<i2')
    occupied = np.zeros(total, dtype=bool)
    previous_source, previous_destination = 0, 0
    source_gaps = []
    pieces = placement['retained_pieces']
    for piece in pieces:
        a, b = piece['source_start_sample'], piece['source_end_sample']
        x, y = piece['destination_start_sample'], piece['destination_end_sample']
        assert 0 <= a < b <= len(fast) and previous_source <= a
        assert previous_destination <= x < y <= total and b - a == y - x
        assert not np.any(occupied[x:y]) and pcmsha(fast[a:b]) == piece['pcm_sha256']
        if a > previous_source:
            source_gaps.append([previous_source, a])
        raw[x:y], occupied[x:y] = fast[a:b], True
        previous_source, previous_destination = b, y
    if previous_source < len(fast):
        source_gaps.append([previous_source, len(fast)])
    removals = placement.get('quiet_removals', [])
    assert source_gaps == [[p['source_start_sample'], p['source_end_sample']] for p in removals], 'Every omitted source range must be an explicitly reviewed quiet removal'
    for a, b in source_gaps:
        assert all(float(np.sqrt(np.mean((fast[s:min(s + 480, b)].astype(np.float64) / 32768) ** 2))) <= 10 ** (-48 / 20) for s in range(a, b, 480)), 'Removed source range is not sustained waveform quiet'
    utterances = placement['utterances']
    assert len(utterances) == 68 and len({u['cut_id'] for u in utterances}) == 68
    protected = []
    for u in utterances:
        a, b = u['source_protected_start_sample'], u['source_protected_end_sample']
        x, y = u['destination_speech_start_sample'], u['destination_speech_end_sample']
        assert 0 <= a < b <= len(fast) and 0 <= x < y <= total and b - a == y - x
        assert np.array_equal(fast[a:b], raw[x:y]), 'Protected utterance changed: ' + u['cut_id']
        protected.append({'cut_id': u['cut_id'], 'source_start_sample': a,
                          'source_end_sample': b, 'destination_start_sample': x,
                          'destination_end_sample': y, 'pcm_sha256': pcmsha(fast[a:b])})
    title_windows, card_windows = [], []
    for entry in timeline['entries']:
        a, b = entry['start_frame'] * 1600, entry['end_frame'] * 1600
        if entry['kind'] == 'title':
            assert b - a == 96000 and not np.any(raw[a:b])
            title_windows.append([a, b])
        if entry['kind'] == 'silent':
            assert b - a == 192000 and not np.any(raw[a:b])
            card_windows.append([a, b])
    assert len(title_windows) == 12 and len(card_windows) == 1
    assert card_windows[0][1] == total
    return raw, protected, title_windows, card_windows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=OUT)
    parser.add_argument('--ffmpeg', default='ffmpeg')
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    audit = out / 'audio-audit'
    audit.mkdir(exist_ok=True)
    descriptor_path = ROOT / 'narration/two-part-sources.json'
    descriptor = load(descriptor_path)
    placement_path = ROOT / 'narration/placement-manifest.json'
    placement = load(placement_path)
    timeline_path = ROOT / 'timeline.json'
    timeline = load(timeline_path)
    cfg_path = ROOT / 'narration/ko.json'
    cfg = load(cfg_path)
    assert timeline['revision'] == 12 and not timeline.get('preview_only', False)
    assert timeline['fps'] == 30 and len(timeline['entries']) == 81
    assert timeline['frames'] <= 9900 and timeline['duration'] <= 330
    assert sum(e['kind'] == 'cut' for e in timeline['entries']) == 68
    assert placement['source_identity_sha256'] == descriptor['source_identity_sha256']
    if 'timeline' in placement:
        assert placement['timeline']['sha256'] == sha(timeline_path)
    fast_binding = placement['fast_master']
    assert fast_binding['sha256'] == descriptor['fast_master']['sha256']
    complete = placement['completeness_review']
    complete_path = path_from(complete['path'])
    coverage = load(complete_path)
    assert sha(complete_path) == complete['sha256'] and str(coverage['status']).startswith('PASS')
    assert coverage['source_identity_sha256'] == descriptor['source_identity_sha256']
    assert coverage['processed_master_sha256'] == descriptor['fast_master']['sha256']
    assert coverage['raw_composite_master_sha256'] == descriptor['composite_master']['sha256']
    assert coverage['sentences_complete'] == 68 and all(coverage['checks'].values())
    assert len(placement.get('boundaries', [])) == 67, 'All67 approved word/wave boundaries are required'
    total = timeline['frames'] * 1600
    original, fast, source_paths, tempo_review = reproduce_source(descriptor, audit, args.ffmpeg)
    raw, protected, titles, cards = assemble(placement, fast, total, timeline)
    rawfile, voicefile = out / 'narration-raw.wav', out / 'narration.wav'
    write(rawfile, raw)
    before = measure(rawfile, args.ffmpeg)
    target = -19.5
    gain_db = target - before['input_i']
    factor = 10 ** (gain_db / 20)
    voice64 = np.rint(raw.astype(np.float64) * factor).astype(np.int64)
    assert np.max(np.abs(voice64)) < 32767, 'Constant target voice gain clips; review the target rather than limiting speech'
    voice = voice64.astype('<i2')
    write(voicefile, voice)
    voice_level = measure(voicefile, args.ffmpeg)
    assert abs(voice_level['input_i'] - target) <= .25 and voice_level['input_tp'] < 0
    source_song = ROOT / cfg['bgm']
    assert sha(source_song) == SONG_SHA, 'Selected original BGM changed'
    decoded_song = audit / 'bgm-original.wav'
    run([args.ffmpeg, '-y', '-v', 'error', '-i', source_song, '-ar', RATE,
         '-ac', '2', '-c:a', 'pcm_s16le', decoded_song])
    loop, musicplan = build_music(read(decoded_song, 2), total)
    loopfile = out / 'bgm-loop.wav'
    write(loopfile, loop)
    basefile, musicfile = audit / 'music-base.wav', audit / 'music-final.wav'
    graph = (f'[0:a]apad=pad_len={RATE}[side];'
             f'[1:a]apad=pad_len={RATE},asplit=2[basepre][music];'
             f'[basepre]atrim=end_sample={total}[base];'
             f'[music][side]sidechaincompress=threshold=0.018:ratio=4:attack=45:'
             f'release=650:makeup=1:mix=0.60,atrim=end_sample={total}[duck]')
    run([args.ffmpeg, '-y', '-v', 'error', '-filter_complex_threads', '1',
         '-i', voicefile, '-i', loopfile, '-filter_complex', graph,
         '-map', '[base]', '-c:a', 'pcm_s16le', basefile,
         '-map', '[duck]', '-c:a', 'pcm_s16le', musicfile])
    base, music = read(basefile, 2), read(musicfile, 2)
    assert len(base) == len(music) == total
    mixed = voice.astype(np.int32) + music.astype(np.int32)
    assert np.max(np.abs(mixed)) < 32767, 'Mix clips; do not add an undisclosed limiter'
    final = out / 'audio.wav'
    write(final, mixed)
    mix_level = measure(final, args.ffmpeg)
    br, mr, vr = rms100(base), rms100(music), rms100(voice)
    time = np.arange(len(mr)) * .1
    core = (time >= 2.1) & (time < total / RATE - 4.1)
    active = core & (db(vr) > -32)
    ratio = np.divide(mr, br, out=np.ones_like(mr), where=br > 1e-9)
    gap = db(vr) - db(mr)
    checks = {
        'two_authorized_raw_parts_and_complete_master_exact': True,
        'one_global_atempo115_reproduction_PCM_exact': True,
        'no_additional_voice_pitch_tempo_EQ_compressor': True,
        'current_completeness_review_PASS': True,
        'all68_protected_utterances_PCM_exact_from_fast_master': len(protected) == 68,
        'all_retained_pieces_copy_at_tempo1_without_overlap': True,
        'source_omissions_equal_only_explicit_reviewed_quiet': True,
        '67_word_waveform_boundary_records_present': len(placement['boundaries']) == 67,
        'twelve_titles_each2s_voice_literal_zero': len(titles) == 12,
        'last4s_card_voice_literal_zero': not np.any(voice[cards[0][0]:]),
        'frame_locked_48k_clock_and_duration_at_most330': len(mixed) == total and total / RATE <= 330,
        'voice_exact_one_constant_gain': np.array_equal(voice, voice64.astype('<i2')),
        'voice_loudness_matches_baseline11_minus19_5': abs(voice_level['input_i'] + 19.5) <= .25,
        'original_BGM_file_identity': sha(source_song) == SONG_SHA,
        'same_BGM_loop_and_duck_policy_new_end_fade': True,
        'music_buffers_flushed_exact_sample_count': len(base) == len(music) == total,
        'no100ms_music_zero_between_fades': not np.any(mr[core] == 0),
        'duck_floor_above_minus8_1dB': float(np.min(db(ratio)[core])) >= -8.1,
        'no_voice_or_mix_sample_clipping': np.max(np.abs(mixed)) < 32767,
        'voice_and_mix_true_peak_below0': voice_level['input_tp'] < 0 and mix_level['input_tp'] < 0,
    }
    gap_p05 = float(np.percentile(gap[active], 5))
    advisory = {'speech_at_least6dB_above_music_in95pct_active_windows': {
        'pass': gap_p05 >= 6, 'target_db': 6, 'actual_db': gap_p05,
        'shortfall_db': max(0., 6 - gap_p05),
        'method': 'P05 voice-minus-music100ms RMS, voice above-32dBFS, outside end fades.',
        'policy': 'Advisory target from the older mix. Preserve the user-requested BGM gain/duck policy and constant voice level; do not alter either to force this target to pass.'}}
    balance_ok = all(item['pass'] for item in advisory.values())
    names = ['narration-raw.wav', 'narration.wav', 'bgm-loop.wav', 'audio.wav']
    files = {name: {'sha256': sha(out / name), 'pcm_sha256': pcmsha(read(out / name, 1 if name.startswith('narration') else 2)),
                    'samples': total, 'sample_rate': RATE, 'channels': 1 if name.startswith('narration') else 2} for name in names}
    paths = [Path(__file__), ROOT / 'authorization.json', descriptor_path,
             placement_path, timeline_path, cfg_path, complete_path, source_song, *source_paths]
    historical = ROOT / 'narration/incomplete-take-review.json'
    historical_info = None
    if historical.exists():
        old = load(historical)
        historical_info = {'receipt': portable(historical), 'sha256': sha(historical),
                           'generation_id': old['generation_id'],
                           'original_master_sha256': old['original_master_sha256'],
                           'role': 'Historical incomplete single take, excluded from all delivered voice.'}
        paths.append(historical)
    report = {
        'revision': 12, 'status': ('PASS' if balance_ok else 'PASS_WITH_BALANCE_CAVEAT') if all(checks.values()) else 'FAIL',
        'generation_mode': descriptor['generation_mode'], 'new_actual_raw_parts': 2,
        'source_identity_sha256': descriptor['source_identity_sha256'],
        'source_descriptor_sha256': sha(descriptor_path), 'timeline_sha256': sha(timeline_path),
        'placement_manifest_sha256': sha(placement_path), 'completeness_review_sha256': sha(complete_path),
        'pitch_cents': 0, 'speech_tempo': 1.15, 'placement_tempo': 1,
        'duration_seconds': total / RATE, 'frames': timeline['frames'], 'samples': total,
        'sample_rate': RATE, 'constant_voice_gain_db': gain_db, 'gain_factor': factor,
        'target_voice_integrated_LUFS': target, 'original_voice_measurement': before,
        'voice_measurement': voice_level, 'mix_measurement': mix_level,
        'quantization': "np.rint(placed_fast_master_int16.astype(float64) * 10**(gain_db/20)).astype('<i2')",
        'tempo_reproduction': tempo_review, 'protected_speech': protected,
        'title_silent_sample_windows': titles, 'final_card_sample_windows': cards,
        'bgm': {**musicplan, 'source': portable(source_song), 'source_sha256': SONG_SHA,
                'minimum_duck_db': float(np.min(db(ratio)[core])),
                'speech_minus_music_db_p05_median_p95': list(map(float, np.percentile(gap[active], [5, 50, 95]))),
                'music_rms_dbfs_p05_median_p95': list(map(float, np.percentile(db(mr)[core], [5, 50, 95]))),
                'note': 'Same song and edit/duck policy; previous fixed-length ducked PCM is not reused.'},
        'duck_filter_graph': graph, 'audio_sha256': sha(final), 'files': files,
        'historical_failed_single_take': historical_info,
        'checks': {k: bool(v) for k, v in checks.items()},
        'core_checks': {k: bool(v) for k, v in checks.items()},
        'advisory_balance_checks': advisory,
        'checks_passed': sum(bool(v) for v in checks.values()), 'checks_total': len(checks),
        'input_bindings': {portable(p): sha(p) for p in dict.fromkeys(paths)},
        'scope': 'Actual two-part source/tempo reproduction, approved PCM placement, constant voice gain and music-envelope checks. Independent speech review, encoded AAC and continuous playback remain separate.',
        'ffmpeg_version': run([args.ffmpeg, '-version']).stdout.splitlines()[0],
    }
    save(out / 'audio-validation.json', report)
    save(ROOT / 'audio-processing-manifest.json', report)
    print(json.dumps({'status': report['status'], 'checks': [report['checks_passed'], report['checks_total']],
                      'duration': total / RATE, 'audio': str(final)}, ensure_ascii=False))
    assert all(checks.values()), checks


if __name__ == '__main__':
    main()
