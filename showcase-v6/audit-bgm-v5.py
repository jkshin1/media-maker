#!/usr/bin/env python3
"""Measure the complete approved music loop and its original ducking, read-only."""
from pathlib import Path
import argparse, hashlib, json, math, subprocess, wave
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / 'out/showcase-v5'
SR = 48000
BODY_START = 39.0
BODY_END = 288.1


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True)


def read_wave(path):
    with wave.open(str(path)) as f:
        assert f.getframerate() == SR and f.getsampwidth() == 2
        params = f.getparams()
        data = f.readframes(f.getnframes())
    return np.frombuffer(data, '<i2').reshape(-1, params.nchannels), params, data


def db(value):
    return 20 * np.log10(np.maximum(value, 1e-12))


def windows(samples, seconds=.1):
    size = round(SR * seconds)
    complete = samples[:len(samples) // size * size].astype(np.float64) / 32768
    shaped = complete.reshape(-1, size, samples.shape[1])
    rms = np.sqrt(np.mean(shaped * shaped, axis=(1, 2)))
    peak = np.max(np.abs(shaped), axis=(1, 2))
    return rms, peak


def spans(mask, step=.1, minimum=.5):
    edges = np.diff(np.r_[False, mask, False].astype(np.int8))
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    return [{'start': round(float(a * step), 4), 'end': round(float(b * step), 4), 'duration': round(float((b-a) * step), 4)}
            for a, b in zip(starts, ends) if (b-a) * step >= minimum]


def ensure_stems():
    OUT.mkdir(parents=True, exist_ok=True)
    folder = OUT / 'audio-audit'
    folder.mkdir(exist_ok=True)
    config = json.loads((ROOT / 'narration/ko.json').read_text())
    timeline = json.loads((ROOT / 'timeline.json').read_text())
    duration = timeline['duration']
    voice = ROOT / 'narration/revision4-narration.wav'
    approved = ROOT / 'narration/revision4-approved-audio.wav'
    bgm = ROOT / config['bgm']
    original = folder / 'original-bgm.wav'
    loop = folder / 'music-original-loop.wav'
    base = folder / 'music-base.wav'
    ducked = folder / 'music-original-ducked.wav'
    reproduced = folder / 'revision4-reproduced.wav'
    proof = folder / 'stems-provenance.json'
    inputs = {str(f.relative_to(ROOT)): sha(f) for f in [voice, approved, bgm]}
    ready = proof.exists() and all(f.exists() for f in [original, loop, base, ducked, reproduced])
    if ready:
        saved = json.loads(proof.read_text())
        ready = saved.get('inputs') == inputs and all(
            saved.get('stems', {}).get(str(f.relative_to(OUT))) == sha(f)
            for f in [original, loop, base, ducked, reproduced])
    if not ready:
        run(['ffmpeg', '-y', '-v', 'error', '-i', str(bgm), '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', str(original)])
        graph = f'[0:a]aresample=48000,asplit=3[a][b][c];[a][b]acrossfade=d=3:c1=tri:c2=tri[ab];[ab][c]acrossfade=d=3:c1=tri:c2=tri,atrim=duration={duration}[music]'
        run(['ffmpeg', '-y', '-v', 'error', '-i', str(bgm), '-filter_complex', graph, '-map', '[music]', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', str(loop)])
        graph = (f'[0:a]apad=pad_dur=1,asplit=2[side][speech];'
                 f'[1:a]apad=pad_dur=1,volume=0.20,afade=t=in:st=0:d=1,afade=t=out:st={duration-1.5}:d=1.5,asplit=2[base][music];'
                 '[base]atrim=duration='+str(duration)+'[baseout];'
                 '[music][side]sidechaincompress=threshold=0.018:ratio=4:attack=18:release=300:makeup=1,asplit=2[duck][mixmusic];'
                 '[duck]atrim=duration='+str(duration)+'[duckout];'
                 '[speech][mixmusic]amix=inputs=2:normalize=0:dropout_transition=0,alimiter=limit=0.841395:level=false,atrim=duration='+str(duration)+'[mix]')
        run(['ffmpeg', '-y', '-v', 'error', '-i', str(voice), '-i', str(loop), '-filter_complex', graph,
             '-map', '[baseout]', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', str(base),
             '-map', '[duckout]', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', str(ducked),
             '-map', '[mix]', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', str(reproduced)])
        proof.write_text(json.dumps({'inputs': inputs, 'duration': duration,
            'original_duck': {'threshold': .018, 'ratio': 4, 'attack_ms': 18, 'release_ms': 300},
            'base_music_gain': .20, 'fade_in_seconds': 1, 'fade_out_seconds': 1.5,
            'stems': {str(f.relative_to(OUT)): sha(f) for f in [original, loop, base, ducked, reproduced]},
            'reproduced_mix_matches_approved_file': sha(reproduced) == sha(approved)}, ensure_ascii=False, indent=2)+'\n')
    return dict(voice=voice, approved=approved, original=original, loop=loop, base=base, ducked=ducked,
                reproduced=reproduced, folder=folder, proof=proof, duration=duration, bgm=bgm)


def main():
    paths = ensure_stems()
    original, original_params, _ = read_wave(paths['original'])
    loop, params, _ = read_wave(paths['loop'])
    base, _, _ = read_wave(paths['base'])
    duck, _, _ = read_wave(paths['ducked'])
    voice, _, _ = read_wave(paths['voice'])
    raw_rms, _ = windows(loop)
    base_rms, _ = windows(base)
    duck_rms, duck_peak = windows(duck)
    voice_rms, _ = windows(voice)
    raw_db, base_db, duck_db = db(raw_rms), db(base_rms), db(duck_rms)
    gain = np.divide(duck_rms, base_rms, out=np.ones_like(duck_rms), where=base_rms > 1e-6)
    gain_db = db(gain)
    t = np.arange(len(gain)) * .1
    body = (t >= BODY_START) & (t < BODY_END)
    active_music = base_db > -48
    active_voice = db(voice_rms) > -42
    reduction = body & active_music & (gain_db < -15)
    source_quiet = body & (raw_db < -45)
    source_duration = len(original) / SR
    crossfades = [{'start': source_duration - 3, 'end': source_duration},
                  {'start': 2 * (source_duration - 3), 'end': 2 * source_duration - 3}]
    trace = []
    for i in range(len(t)):
        trace.append({'time': round(float(t[i]), 3), 'raw_loop_rms_dbfs': round(float(raw_db[i]), 3),
                      'base_music_rms_dbfs': round(float(base_db[i]), 3),
                      'original_ducked_music_rms_dbfs': round(float(duck_db[i]), 3),
                      'original_duck_gain_db': round(float(gain_db[i]), 3),
                      'narration_rms_dbfs': round(float(db(voice_rms[i])), 3)})
    measurements = {
        'body_duck_gain_min_db': float(np.min(gain_db[body & active_music])),
        'body_duck_gain_percentiles_db': dict(zip(['p05','p25','p50','p75','p95'], map(float, np.percentile(gain_db[body & active_music], [5,25,50,75,95])))),
        'body_with_music_under_minus_48_dbfs_seconds': float(np.count_nonzero(body & (duck_db < -48)) * .1),
        'body_with_music_under_minus_54_dbfs_seconds': float(np.count_nonzero(body & (duck_db < -54)) * .1),
        'body_source_quiet_below_minus_45_dbfs_seconds': float(np.count_nonzero(source_quiet) * .1),
        'body_ducking_below_minus_15_db_seconds_when_music_source_active': float(np.count_nonzero(reduction) * .1),
        'music_base_rms_percentiles_dbfs': list(map(float, np.percentile(base_db[body], [5,50,95]))),
        'music_ducked_rms_percentiles_dbfs': list(map(float, np.percentile(duck_db[body], [5,50,95]))),
        'body_zero_music_100ms_windows': int(np.count_nonzero(body & (duck_peak == 0))),
    }
    low = spans(body & (duck_db < -48), minimum=.5)
    for region in low:
        a, b = round(region['start'] * 10), round(region['end'] * 10)
        region['raw_loop_rms_median_dbfs'] = float(np.median(raw_db[a:b]))
        region['base_music_rms_median_dbfs'] = float(np.median(base_db[a:b]))
        region['ducked_music_rms_median_dbfs'] = float(np.median(duck_db[a:b]))
        region['duck_reduction_median_db'] = float(np.median(gain_db[a:b]))
        region['source_already_very_quiet'] = bool(np.median(raw_db[a:b]) < -45)
    report = {'status': 'AUDITED', 'duration': paths['duration'], 'sample_rate': SR,
              'body_scope_seconds': [BODY_START, BODY_END], 'track_decoded_duration_seconds': source_duration,
              'track_file_duration_seconds': float(json.loads(run(['ffprobe','-v','error','-show_format','-of','json',str(paths['bgm'])]).stdout)['format']['duration']),
              'loop_method': 'Three complete copies, two three-second triangular crossfades, clipped at the original film duration.',
              'crossfade_windows': crossfades, 'old_settings': {'music_gain': .20, 'threshold': .018, 'ratio': 4, 'attack_ms': 18, 'release_ms': 300},
              'measurements': measurements, 'music_low_regions': low,
              'raw_source_quiet_regions': spans(source_quiet, minimum=.5),
              'excessive_ducking_regions': spans(reduction, minimum=.5),
              'complete_100ms_trace': trace,
              'reproduction': json.loads(paths['proof'].read_text()),
              'inputs_sha256': {str(f.relative_to(ROOT)): sha(f) for f in [paths['voice'], paths['approved'], paths['bgm']]},
              'scope': 'Full-length objective stem inspection, not a subjective listening acceptance.'}
    (OUT / 'bgm-audit-before.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'status': report['status'], 'source_seconds': source_duration, 'crossfades': crossfades,
                      'measurements': measurements, 'low_regions': low,
                      'report': str(OUT / 'bgm-audit-before.json')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
