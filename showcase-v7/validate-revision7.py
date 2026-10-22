#!/usr/bin/env python3
"""Assemble the final Revision7 receipt after all media and QA are complete.

The visual change is local 2D mesh motion of existing first-photo images.
This validator does not generate footage, narration, audio, or video.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess

from audio import audio_hash

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / 'out/showcase-v7'
FINAL = OUT / 'RD_Process_AI_Fast_Track_Showcase_Revision7.mp4'
FPS = 30
FRAMES = 9214
DURATION = FRAMES / FPS
MOTION_INPUTS = {
    'photo-motion.js', 'photo-motion-early.json',
    'photo-motion-middle.json', 'photo-motion-late.json',
}
CORE_INPUTS = MOTION_INPUTS | {
    'spec.json', 'timeline.json', 'stage.mjs', 'task-scenes.js',
    'task-visuals-early.js', 'task-visuals-late.js', 'hero-scenes.js',
}
RECEIPTS = {
    'scope': 'photo-motion-validation.json',
    'native': 'native-motion-visual-review.json',
    'encoded': 'encoded-visual-review.json',
    'playback': 'playback-validation.json',
    'audio': 'audio-validation.json',
    'mux': 'mux-validation.json',
    'render': 'render-validation.json',
}


def load(path):
    return json.loads(path.read_text())


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while block := f.read(8 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()


def source_path(name):
    # Native visual receipts use project-relative names; scope/render use
    # source-directory-relative names. Both resolve to this revision only.
    name = str(name)
    p = (ROOT.parent / name if name.startswith(ROOT.name + '/')
         else ROOT / name).resolve()
    if not p.is_relative_to(ROOT):
        raise ValueError('Source receipt points outside this revision: ' + name)
    return p


def normalized_names(hashes):
    return {str(source_path(name).relative_to(ROOT)) for name in hashes}


def current_hashes(hashes):
    if not isinstance(hashes, dict) or not hashes:
        return False
    return all(isinstance(value, str) and source_path(name).is_file()
               and sha(source_path(name)) == value
               for name, value in hashes.items())


def passed_checks(checks):
    return bool(checks) and all(
        item.get('pass') is True if isinstance(item, dict) else item is True
        for item in checks.values())


def command(args):
    return subprocess.run(args, check=True, capture_output=True, text=True)


def video_payload_hash(path):
    return command([
        'ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:v:0',
        '-c', 'copy', '-f', 'hash', '-hash', 'sha256', '-']).stdout.strip()


def render_input_names(spec):
    names = set(CORE_INPUTS)
    names.update({
        'fonts/NotoSansCJKkr-Regular.otf', 'fonts/NotoSansCJKkr-Bold.otf',
    })
    names.update(f'assets/opening/cut{i:02}.png' for i in range(1, 10))
    names.update(spec.get('microscopy', {}).values())
    for section in spec['sections']:
        if section.get('reference_image'):
            names.add(section['reference_image'])
        backgrounds = section.get('backgrounds') or []
        photos = section.get('photo_crops') or []
        names.update(f for f in backgrounds if f)
        for i, cut in enumerate(section['cuts']):
            chosen = ((backgrounds[i] if i < len(backgrounds) else None)
                      or cut.get('photo_crop') or cut.get('background')
                      or (photos[i] if i < len(photos) else None))
            if chosen:
                names.add(chosen)
    return names


def main():
    checks, details = {}, {}

    def gate(name, passed, **detail):
        checks[name] = bool(passed)
        if detail:
            details[name] = detail

    def write_result(file_sha=None, inputs=None, receipts=None):
        report = {
            'status': 'PASS' if checks and all(checks.values()) else 'FAIL',
            'revision': 7,
            'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'checks': checks, 'check_details': details,
            'file': str(FINAL), 'sha256': file_sha,
            'duration_seconds': DURATION, 'frames': FRAMES, 'fps': FPS,
            'visual_scope': (
                'Only the twelve task first-photo cuts gain small local human, '
                'hand and prop posture motion by continuous 2D mesh resampling '
                'of their existing photographs. Camera-held QA separately '
                'checks the local movement. No generated human footage, hidden '
                'surfaces, new image content or new narration is claimed.'),
            'preservation_scope': (
                'The other 75 entries are compared at three post-dissolve '
                'positions each: 225 exact RGBA samples. This is sampled '
                'native equality, not an all-frame encoded identity claim. '
                'The existing outgoing first-photo 0.45-second dissolve may '
                'naturally reflect its changed photographic frame.'),
            'audio_scope': (
                'Complete approved Revision5 AAC payload and decoded 48000 Hz '
                'stereo s16le PCM must match exactly. Narration, BGM, speed '
                'and mix remain unchanged; no audio encoding or TTS is run.'),
            'continuous_playback_scope': (
                'Muted browser playback at 1x from zero to ended is separate '
                'from exact audio validation and sampled visual judgement.'),
            'input_hashes': inputs or [], 'receipts': receipts or {},
        }
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / 'final-validation.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({
            'status': report['status'], 'passed': sum(checks.values()),
            'total': len(checks),
            'failed': [key for key, value in checks.items() if not value],
            'duration': DURATION, 'sha256': file_sha,
        }, ensure_ascii=False))
        return 0 if report['status'] == 'PASS' else 2

    missing = [str(p) for p in [FINAL, ROOT / 'spec.json', ROOT / 'timeline.json',
                              *(OUT / f for f in RECEIPTS.values())]
               if not p.is_file()]
    gate('required_final_media_and_receipts_present', not missing,
         missing=missing)
    if missing:
        return write_result()

    receipt_rows = {key: {'path': str(OUT / name), 'sha256': sha(OUT / name)}
                    for key, name in RECEIPTS.items()}
    documents = {key: load(OUT / name) for key, name in RECEIPTS.items()}
    scope, native, encoded, playback, audio, mux, render = (
        documents[key] for key in
        ['scope', 'native', 'encoded', 'playback', 'audio', 'mux', 'render'])
    spec, tl = load(ROOT / 'spec.json'), load(ROOT / 'timeline.json')
    final_sha, silent = sha(FINAL), OUT / 'video_silent.mp4'
    inputs = render.get('inputs', [])
    task_ids = {s['id'] for s in spec['sections'] if s['type'] == 'task'}

    gate('photo_motion_scope_technical_checks_pass',
         scope.get('status') == 'PASS' and passed_checks(scope.get('checks')))
    expected_counts = {'first_photo': 12, 'functional_body': 48,
                       'task_title': 12, 'hero': 15}
    rows = scope.get('entries', [])
    first = [r for r in rows if r.get('kind') == 'first_photo']
    gate('only_twelve_first_photos_with_87_entry_coverage',
         len(task_ids) == 12 and len(tl['entries']) == len(rows) == 87
         and scope.get('counts') == expected_counts
         and len(first) == 12
         and {r['section_id'] for r in first} == task_ids
         and all(r.get('cut_index') == 0 for r in first))
    scope_hashes = scope.get('source_hashes', {})
    gate('scope_review_source_hashes_current',
         current_hashes(scope_hashes)
         and CORE_INPUTS.issubset(normalized_names(scope_hashes)))

    other = [r for r in rows if r.get('kind') != 'first_photo']
    other_samples = [s for r in other for s in r.get('samples', [])]
    gate('other_75_entries_225_samples_exact_rgba',
         len(other) == 75 and all(len(r.get('samples', [])) == 3 for r in other)
         and len(other_samples) == 225
         and all(s.get('exact_rgba_equal') is True for s in other_samples))
    all_samples = [s for r in rows for s in r.get('samples', [])]
    gate('motion_toggle_off_restores_261_samples_exactly',
         len(all_samples) == 261
         and all(s.get('toggle_off_exact_rgba_equal') is True
                 for s in all_samples))
    frozen = scope.get('camera_frozen', [])
    gate('camera_independent_motion_evidenced_for_all_twelve',
         len(frozen) == 12
         and {r['section_id'] for r in frozen} == task_ids
         and all(len(r.get('samples', [])) == 3
                 and all(s.get('changed_header_pixels') == 0
                         for s in r['samples'])
                 and any(s.get('changed_body_pixels', 0) > 0
                         for s in r['samples']) for r in frozen))
    native_hashes = native.get('source_hashes', {})
    gate('native_motion_visual_review_complete_and_current',
         native.get('status') == 'PASS' and native.get('reviewed_tasks') == 12
         and native.get('passed_tasks') == 12
         and native.get('blocking_artifacts') == []
         and current_hashes(native_hashes)
         and MOTION_INPUTS.issubset(normalized_names(native_hashes)))
    gate('decoded_final_visual_review_pass_for_this_video',
         encoded.get('status') == 'PASS'
         and encoded.get('video_sha256') == final_sha)

    gate('locked_timeline_307_133_seconds_and_9214_frames',
         tl['frames'] == FRAMES and tl['fps'] == FPS
         and abs(tl['duration'] - DURATION) < 1e-9
         and tl.get('allow_over_five_minutes') is True)
    meta = json.loads(command([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format',
        '-of', 'json', str(FINAL)]).stdout)
    videos = [s for s in meta['streams'] if s['codec_type'] == 'video']
    audios = [s for s in meta['streams'] if s['codec_type'] == 'audio']
    video = videos[0] if len(videos) == 1 else {}
    sound = audios[0] if len(audios) == 1 else {}
    gate('fullhd_h264_30fps_9214_frames',
         video.get('width') == 1920 and video.get('height') == 1080
         and video.get('codec_name') == 'h264'
         and video.get('r_frame_rate') == '30/1'
         and int(video.get('nb_frames', -1)) == FRAMES)
    actual_duration = float(meta['format']['duration'])
    gate('final_duration_matches_locked_timeline',
         abs(actual_duration - DURATION) < 2 / FPS,
         actual_seconds=actual_duration,
         expected_seconds=DURATION, tolerance_seconds=2 / FPS)
    gate('aac_48000_hz_stereo', sound.get('codec_name') == 'aac'
         and sound.get('sample_rate') == '48000' and sound.get('channels') == 2)
    unchanged_audio = ['new_tts', 'mix_changed', 'voice_speed_changed',
                       'narration_changed', 'bgm_changed']
    approved = source_path(audio['source_audio_file'])
    gate('approved_audio_receipt_and_source_unchanged',
         audio.get('status') == 'PASS' and passed_checks(audio.get('checks'))
         and all(audio.get(key) is False for key in unchanged_audio)
         and approved.is_file()
         and sha(approved) == audio.get('approved_aac_file_sha256'))
    aac_hash, pcm_hash = audio_hash(FINAL), audio_hash(FINAL, True)
    gate('complete_approved_aac_packets_exact',
         aac_hash == audio.get('aac_packet_payload_hash'), actual=aac_hash)
    gate('complete_approved_decoded_pcm_exact',
         pcm_hash == audio.get('decoded_48000_stereo_s16le_hash'), actual=pcm_hash)
    gate('mux_copies_both_streams_without_audio_encoding_or_tts',
         mux.get('status') == 'PASS'
         and mux.get('video_stream_copied') is True
         and mux.get('audio_stream_copied') is True
         and mux.get('audio_reencoded') is False and mux.get('new_tts') is False)
    gate('render_and_mux_file_hashes_current',
         render.get('status') == 'PASS' and silent.is_file()
         and sha(silent) == render.get('sha256') == mux.get('silent_video_sha256')
         and final_sha == mux.get('final_sha256'))
    input_map = {r['file']: r['sha256'] for r in inputs}
    required_inputs = render_input_names(spec)
    gate('all_render_inputs_including_motion_code_and_three_configs_current',
         bool(inputs) and len(inputs) == len(input_map)
         and required_inputs.issubset(normalized_names(input_map))
         and current_hashes(input_map),
         recorded_count=len(inputs), required_count=len(required_inputs),
         missing_required=sorted(required_inputs - normalized_names(input_map)))
    payloads = [video_payload_hash(p) for p in [silent, FINAL]]
    gate('video_packet_payload_copied_exactly', payloads[0] == payloads[1],
         payload_hash=payloads[0])
    end = playback.get('final', {})
    gate('continuous_muted_1x_playback_zero_to_ended_complete',
         playback.get('status') == 'PASS'
         and playback.get('sha256') == playback.get('sha256_after_playback') == final_sha
         and playback.get('started_media_time') == 0
         and playback.get('ended_event') is True and end.get('ended') is True
         and end.get('playbackRate') == 1 and end.get('muted') is True
         and playback.get('seeks_during_playback') == 0
         and playback.get('pauses_during_playback') == 0
         and playback.get('playback_wall_seconds', 0) >= DURATION - .75)
    decoded = command(['ffmpeg', '-v', 'error', '-nostats', '-i', str(FINAL),
                       '-map', '0:v:0', '-map', '0:a:0', '-progress', 'pipe:1',
                       '-f', 'null', '-'])
    progress = dict(line.split('=', 1) for line in decoded.stdout.splitlines()
                    if '=' in line)
    gate('complete_video_and_audio_decode_without_errors',
         not decoded.stderr.strip() and progress.get('progress') == 'end'
         and int(progress.get('frame', -1)) == FRAMES,
         stderr=decoded.stderr.strip(), decoded_frames=progress.get('frame'),
         decode_progress=progress.get('progress'))
    return write_result(final_sha, inputs, receipt_rows)


if __name__ == '__main__':
    raise SystemExit(main())
