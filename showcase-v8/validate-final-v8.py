#!/usr/bin/env python3
"""Bind completed media checks to the current Revision8 files. Does not render."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
OUT = WORKSPACE / 'out/showcase-v8'
VIDEO = OUT / 'RD_Process_AI_Fast_Track_Showcase_Revision8.mp4'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def passed_checks(value):
    if isinstance(value, dict):
        return bool(value) and all(v is True or isinstance(v, dict) and
               (v.get('pass') is True or v.get('status') == 'PASS') for v in value.values())
    if isinstance(value, list):
        return bool(value) and all(v.get('pass') is True or v.get('status') == 'PASS' for v in value)
    return False


def source_path(name):
    p = Path(name)
    if p.is_absolute():
        return p
    return WORKSPACE / p if p.parts[0] in {'showcase-v6', 'showcase-v8', 'out'} else ROOT / p


def main():
    names = ['render-validation.json', 'visual-validation.json', 'audio-validation.json',
             'mux-validation.json', 'playback-validation.json', 'revision8-content-validation.json',
             'native-visual-review.json', 'camera-validation.json', 'narration-coverage-validation.json',
             'independent-audio-review.json', 'encoded-audio-validation.json', 'encoded-visual-review.json']
    missing = [n for n in names if not (OUT / n).exists()]
    if missing:
        raise RuntimeError('Required completed checks are missing: ' + ', '.join(missing))
    reports = {n: json.loads((OUT / n).read_text()) for n in names}
    tl = json.loads((ROOT / 'timeline.json').read_text())
    video_hash = sha(VIDEO)
    report = {'status': 'FAIL', 'revision': 8, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'scope': 'Current completed final media, source/PCM bindings and continuous muted browser playback. Source archive reproduction is a separate receipt.',
              'final_sha256': video_hash, 'duration_seconds': tl['duration'], 'frames': tl['frames'],
              'preview_only': False, 'checks': {}, 'receipts': []}

    def check(key, ok, details=None):
        report['checks'][key] = {'pass': bool(ok), 'details': details}

    for name, r in reports.items():
        check('receipt_' + name, r.get('status') == 'PASS', {'status': r.get('status')})
        if 'checks' in r:
            check('gates_' + name, passed_checks(r['checks']))
        report['receipts'].append({'file': name, 'sha256': sha(OUT / name), 'status': r.get('status')})
    for name in ['mux-validation.json', 'playback-validation.json', 'encoded-audio-validation.json', 'encoded-visual-review.json']:
        r = reports[name]
        hashes = [r.get(k) for k in ('sha256', 'file_sha256', 'video_sha256', 'final_sha256')]
        check('video_binding_' + name, video_hash in hashes)

    mismatches = []
    count = 0
    for name, r in reports.items():
        rows = r.get('inputs', []) + r.get('input_bindings', [])
        rows += [{'file': k, 'sha256': v} for k, v in r.get('source_hashes', {}).items()]
        for row in rows:
            p = source_path(row['file'])
            count += 1
            if not p.is_file() or sha(p) != row['sha256']:
                mismatches.append({'receipt': name, 'file': row['file']})
    check('all_current_source_bindings', not mismatches, {'bindings': count, 'mismatches': mismatches})
    check('silent_render_and_pcm_bound', sha(OUT / 'video_silent.mp4') == reports['render-validation.json']['sha256']
          and sha(OUT / 'audio.wav') == reports['audio-validation.json']['audio_sha256']
          == reports['mux-validation.json']['pcm_mix_sha256'])

    p = reports['playback-validation.json']
    check('continuous_whole_browser_playback', p.get('ended_event') is True
          and p.get('loadedmetadata') is True and p.get('play_promise_resolved') is True
          and p.get('started_media_time') == 0 and p.get('seeks_during_playback') == 0
          and p.get('pauses_during_playback') == 0 and len(p.get('screenshot_samples', [])) == 89
          and p.get('sha256_after_playback') == video_hash
          and not any(p.get(k) for k in ('page_errors', 'media_errors', 'http_errors', 'suspicious_black_samples'))
          and p.get('expected', {}).get('frames') == tl['frames'],
          {'screenshots': len(p.get('screenshot_samples', [])), 'muted': True, 'speed': 1,
           'scope': 'Video decode and sampled visual checks; no subjective hearing claim.'})
    check('actual_timeline_and_unmodified_speed', tl.get('preview_only') is False and tl['tempo'] == 1
          and tl['frames'] == 12205 and len(tl['entries']) == 87 and len(tl['audio_segments']) == 60
          and tl.get('allow_over_five_minutes') is True)

    # Recheck the accepted baseline without mutating its source or receipts.
    baseline = json.loads((ROOT / 'revision6-baseline-provenance.json').read_text())
    changed = [r['file'] for r in baseline['files']
               if sha(WORKSPACE / 'showcase-v6' / r['file']) != r['sha256']]
    check('accepted_revision6_source_unchanged', not changed, {'files': len(baseline['files']), 'changed': changed})
    check('accepted_revision6_video_unchanged', sha(WORKSPACE / 'out/showcase-v6/RD_Process_AI_Fast_Track_Showcase_Revision6.mp4')
          == 'fda536f61d1fba62a920b4cbbd64e5fb1b9739868e52282a317a5e4d9a4e2e3c')
    check('accepted_revision6_archive_unchanged', sha(WORKSPACE / 'out/showcase-v6/RD_Process_AI_Fast_Track_Showcase_Revision6_Source.zip')
          == 'bf0960fc235588c1386447dc6959a23233527d495b1e8df716cebc10d8205269')
    report['checks_passed'] = sum(c['pass'] for c in report['checks'].values())
    report['checks_total'] = len(report['checks'])
    report['status'] = 'PASS' if report['checks_passed'] == report['checks_total'] else 'FAIL'
    report['production_complete'] = report['status'] == 'PASS'
    report['limitations'] = ['ASR spelling/abbreviation variants are retained in narration coverage, without evidence of omitted sentences.',
                             'Approved opening/ending PCM are identical before the new AAC encode; old AAC packets are not identical.',
                             'Whole muted browser playback and objective audio measurements do not constitute subjective listening approval.',
                             'Source archive inventory and fresh 87-PNG/four-WAV reproduction are separate checks.']
    (OUT / 'final-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'checks_passed': report['checks_passed'], 'checks_total': report['checks_total'], 'video_sha256': video_hash}))
    if report['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
