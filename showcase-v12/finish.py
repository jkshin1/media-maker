#!/usr/bin/env python3
"""Encode Revision12's PCM mix once, copy the new visual stream, and verify AV."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / 'out/showcase-v12'
NAME = 'RD_Process_AI_Fast_Track_Showcase_Revision12.mp4'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False) + '\n')


def run(args):
    return subprocess.run([str(a) for a in args], check=True,
                          capture_output=True, text=True)


def streamhash(path, stream, ffmpeg):
    return run([ffmpeg, '-v', 'error', '-i', path, '-map', '0:' + stream,
                '-c', 'copy', '-f', 'hash', '-hash', 'sha256', '-']).stdout.strip()


def probe(path, ffprobe):
    return json.loads(run([ffprobe, '-v', 'error', '-show_streams',
                           '-show_format', '-of', 'json', path]).stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--silent', type=Path, default=OUT / 'video_silent.mp4')
    parser.add_argument('--output-dir', type=Path, default=OUT)
    parser.add_argument('--validate-existing', action='store_true')
    parser.add_argument('--ffmpeg', default='ffmpeg')
    parser.add_argument('--ffprobe', default='ffprobe')
    args = parser.parse_args()
    out = args.output_dir.resolve()
    audio_path = out / 'audio-validation.json'
    review_path = out / 'independent-audio-validation.json'
    audio, review = load(audio_path), load(review_path)
    timeline_path = ROOT / 'timeline.json'
    timeline = load(timeline_path)
    assert audio['status'].startswith('PASS') and all(audio['checks'].values())
    assert str(review['status']).startswith('PASS') and all(review['checks'].values())
    assert audio['timeline_sha256'] == review['timeline_sha256'] == sha(timeline_path)
    assert audio['source_identity_sha256'] == review['source_identity_sha256']
    for path, digest in review['input_bindings'].items():
        assert sha(ROOT / path) == digest, 'Stale independent audio input: ' + path
    assert audio['speech_tempo'] == 1.15 and audio['pitch_cents'] == 0
    assert not timeline.get('preview_only', False) and len(timeline['entries']) == 81
    for path, digest in audio['input_bindings'].items():
        assert sha(ROOT / path) == digest, 'Stale audio input: ' + path
    for name, item in audio['files'].items():
        assert sha(out / name) == item['sha256'], 'Stale audio output: ' + name
    assert review['audio_sha256'] == sha(out / 'audio.wav')
    silent = args.silent.resolve()
    final = out / NAME
    reference = out / 'audio-audit/mix-aac.m4a'
    reference.parent.mkdir(exist_ok=True)
    mix = out / 'audio.wav'
    silent_before = sha(silent)
    mix_before = sha(mix)
    if not args.validate_existing:
        # One AAC encoding is retained separately; the delivery mux copies both
        # this encoded audio and the newly rendered silent video's packets.
        run([args.ffmpeg, '-y', '-v', 'error', '-i', mix, '-map', '0:a:0',
             '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-ac', '2',
             '-map_metadata', '-1', '-movflags', '+faststart', reference])
        run([args.ffmpeg, '-y', '-v', 'error', '-i', silent, '-i', reference,
             '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'copy',
             '-map_metadata', '-1', '-movflags', '+faststart', final])
    meta, silent_meta = probe(final, args.ffprobe), probe(silent, args.ffprobe)
    videos = [s for s in meta['streams'] if s['codec_type'] == 'video']
    audios = [s for s in meta['streams'] if s['codec_type'] == 'audio']
    assert len(videos) == len(audios) == 1
    v, a = videos[0], audios[0]
    frames = timeline['frames']
    duration = frames / 30
    vh = streamhash(final, 'v:0', args.ffmpeg)
    sh = streamhash(silent, 'v:0', args.ffmpeg)
    ah = streamhash(final, 'a:0', args.ffmpeg)
    rh = streamhash(reference, 'a:0', args.ffmpeg)
    checks = {
        'current_audio_and_independent_PCM_receipts_PASS': True,
        'current_81entry_timeline_12titles_and_finalcard': len(timeline['entries']) == 81,
        'video_packets_exact_new_silent_render': vh == sh,
        'AAC_packets_exact_single_encoded_reference': ah == rh,
        'H264_1920x1080_30fps': v['codec_name'] == 'h264' and (v['width'], v['height']) == (1920, 1080) and v['avg_frame_rate'] == '30/1',
        'strict_expected_video_frame_count': int(v['nb_frames']) == frames,
        'video_container_and_audio_clocks_within1ms': max(abs(float(v['duration']) - duration), abs(float(a['duration']) - duration), abs(float(meta['format']['duration']) - duration)) <= .001,
        'duration_at_most330seconds': duration <= 330 and float(meta['format']['duration']) <= 330.001,
        'AAC48k_stereo': a['codec_name'] == 'aac' and int(a['sample_rate']) == 48000 and a['channels'] == 2,
        'streams_start_at_zero': abs(float(v.get('start_time', 0))) <= .001 and abs(float(a.get('start_time', 0))) <= .001,
        'silent_render_contains_no_audio': not any(s['codec_type'] == 'audio' for s in silent_meta['streams']),
    }
    # Decode every video frame and audio packet. No -t, -shortest, seeks, or
    # error-concealment option may turn a shortened stream into a passing film.
    run([args.ffmpeg, '-v', 'error', '-xerror', '-err_detect', 'explode',
         '-i', final, '-map', '0:v:0', '-map', '0:a:0', '-f', 'null', '-'])
    checks['whole_video_and_audio_strict_decode'] = True
    checks['all_frozen_inputs_unchanged_during_mux'] = sha(silent) == silent_before and sha(mix) == mix_before and sha(timeline_path) == audio['timeline_sha256']
    report = {
        'revision': 12, 'status': ('PASS' if all(x['pass'] for x in audio.get('advisory_balance_checks', {}).values()) else 'PASS_WITH_BALANCE_CAVEAT') if all(checks.values()) else 'FAIL',
        'final_video': final.name, 'final_video_sha256': sha(final),
        'final_sha256': sha(final), 'video_stream_sha256': vh,
        'silent_file': str(silent), 'silent_sha256': silent_before,
        'AAC_reference': str(reference), 'AAC_reference_sha256': sha(reference),
        'audio_stream_sha256': ah, 'reference_audio_stream_sha256': rh,
        'pcm_mix_sha256': mix_before, 'narration_sha256': sha(out / 'narration.wav'),
        'timeline_sha256': sha(timeline_path), 'source_identity_sha256': audio['source_identity_sha256'],
        'duration_seconds': duration, 'frames': frames,
        'speech_tempo': 1.15, 'pitch_cents': 0,
        'generation_mode': audio['generation_mode'],
        'audio_validation_sha256': sha(audio_path),
        'independent_audio_validation_sha256': sha(review_path),
        'checks': checks, 'checks_passed': sum(checks.values()), 'checks_total': len(checks),
        'advisory_balance_checks': audio.get('advisory_balance_checks', {}),
        'metadata': meta,
        'input_bindings': {'finish.py': sha(Path(__file__)), 'timeline.json': sha(timeline_path),
                           'audio-processing-manifest.json': sha(ROOT / 'audio-processing-manifest.json')},
        'method': 'Encode the actual PCM mix once to AAC256k, then copy both the new silent-video packets and AAC reference packets. Decode the complete resulting AV strictly.',
        'scope': 'Current AV structure, copied packet identity and complete decode. Linguistic completion, subjective tone and continuous browser playback use separate evidence.',
    }
    save(out / 'mux-validation.json', report)
    print(json.dumps({'status': report['status'], 'sha256': report['final_sha256'],
                      'frames': frames, 'duration': duration, 'checks': [report['checks_passed'], report['checks_total']]}))
    assert all(checks.values()), checks


if __name__ == '__main__':
    main()
