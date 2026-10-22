#!/usr/bin/env python3
"""Build reviewed Revision12 timing and exact fast-master PCM placements.

No audio is written or transformed. All samples of the authorized continuous
1.15x master are retained once. Only the12 restored two-second titles, frame
padding, budgeted opening/ending readability holds and final4s card add quiet.
The production path requires independent current-source completeness first.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import wave

ROOT = Path(__file__).resolve().parent
RATE = 48000
FPS = 30
FRAME_SAMPLES = RATE // FPS
MAX_FRAMES = 330 * FPS
TITLE_FRAMES = 60
CARD_FRAMES = 120


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pcmsha(content):
    return hashlib.sha256(content).hexdigest()


def rooted(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def portable(path):
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(Path(path).resolve())


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def read_master(path):
    with wave.open(str(path)) as stream:
        assert (stream.getframerate(), stream.getnchannels(), stream.getsampwidth(), stream.getcomptype()) == (RATE, 1, 2, 'NONE')
        count = stream.getnframes()
        content = stream.readframes(count)
    assert len(content) == count * 2
    return count, content


def completeness(path, alignment, required):
    if not path.exists():
        assert not required, 'Current-source independent68-line completeness review is missing.'
        return {'path': portable(path), 'status': 'PENDING', 'sha256': None}
    review = load(path)
    assert str(review['status']).startswith('PASS'), 'Independent completeness review is not PASS.'
    assert review['source_identity_sha256'] == alignment['source_identity_sha256']
    count = review.get('sentences_complete', review.get('spoken_lines_present', review.get('sentences_present')))
    assert count == 68, 'Independent review must explicitly confirm all68 utterances.'
    bound = review.get('processed_master_sha256', review.get('fast_master_sha256', review.get('master_sha256')))
    if bound is not None:
        assert bound == alignment['master_sha256'], 'Completeness review belongs to a different processed master.'
    return {'path': portable(path), 'sha256': sha(path), 'status': review['status'],
            'source_identity_sha256': review['source_identity_sha256'], 'sentences_complete': count}


def endpoints(cut, previous, following, count):
    """Conservative source speech bounds, preserving raw ASR evidence separately."""
    start = cut['word_start_sample']
    end = cut['word_end_sample']
    if previous:
        if 'current_master_review' in previous:
            start = int(previous['current_master_review']['actual_next_speech_start_sample'])
        else:
            start = min(start, previous['quiet']['end_sample'])
    else:
        start = 0
    if following:
        if 'current_master_review' in following:
            end = int(following['current_master_review']['actual_previous_speech_end_sample'])
        else:
            end = max(end, following['quiet']['start_sample'])
    else:
        end = count
    assert 0 <= start <= end <= count
    assert cut['source_start_sample'] <= start <= end <= cut['source_end_sample'], f"Speech endpoint escapes reviewed source partition: {cut['id']}"
    return start, end


def allocate_readability(units, budget):
    deficits = [max(0, unit['baseline_minimum_frames'] - unit['minimum_frames']) for unit in units]
    requested = sum(deficits)
    if requested <= budget:
        return deficits, requested
    if not requested:
        return [0] * len(units), 0
    allocation = [deficit * budget // requested for deficit in deficits]
    remainder = budget - sum(allocation)
    order = sorted(range(len(units)), key=lambda i: (deficits[i] * budget % requested, -i), reverse=True)
    for index in order[:remainder]:
        allocation[index] += 1
    assert sum(allocation) == budget and all(a <= b for a, b in zip(allocation, deficits))
    return allocation, requested


def build(args):
    alignment, config, spec = load(args.alignment), load(args.config), load(args.spec)
    assert alignment['revision'] == 12 and alignment['generation_mode'] == 'two_part_with_user_authorization'
    assert alignment['ready_for_timeline_review'] is True
    assert alignment['all67_word_waveform_boundaries_confirmed'] is True
    assert alignment['all68_contiguous_segments_cover_master0_to_EOF_exact'] is True
    assert alignment['sentence_count'] == 68 and alignment['safe_boundary_count'] == 67
    assert alignment['config_sha256'] == sha(args.config)
    for name, expected in alignment['input_bindings'].items():
        assert sha(rooted(name)) == expected, f'Alignment input changed: {name}'
    review = completeness(args.completeness_review, alignment, not args.analysis_only)
    source_path = rooted(alignment['master'])
    assert sha(source_path) == alignment['master_sha256']
    count, pcm = read_master(source_path)
    assert count == alignment['master_samples'] and pcmsha(pcm) == alignment['master_pcm_sha256']
    assert alignment['speech_tempo_requested'] == 1.15 and alignment['pitch_cents_requested'] == 0
    baseline = load(args.baseline)
    baseline_outer = {entry['cut_id']: entry['end_frame'] - entry['start_frame']
                      for entry in baseline['entries'] if entry['kind'] == 'cut' and entry['section_id'] in ['opening', 'ending']}
    cuts = alignment['cuts']
    cut_ids = [cut['id'] for cut in cuts]
    assert cut_ids == [cut['id'] for block in config['blocks'] for cut in block['cuts']]
    by_section = {section['id']: section for section in spec['sections']}
    tasks = [block['section_id'] for block in config['blocks'] if by_section[block['section_id']]['type'] == 'task']
    assert len(tasks) == 12
    boundary_by_after = {boundary['after_cut']: boundary for boundary in alignment['boundaries']}
    boundary_by_before = {boundary['before_cut']: boundary for boundary in alignment['boundaries']}
    units = []
    # Opening/ending are split only at confirmed sentence quiet so any added
    # readability hold follows a complete phrase. Task audio stays continuous
    # within each whole paragraph, independently of its internal visual cuts.
    for block in config['blocks']:
        group = [cut for cut in cuts if cut['section_id'] == block['section_id']]
        groups = [[cut] for cut in group] if block['section_id'] in ['opening', 'ending'] else [group]
        for unit_group in groups:
            a, b = unit_group[0]['source_start_sample'], unit_group[-1]['source_end_sample']
            assert a is not None and b is not None and a < b
            units.append({'section_id': block['section_id'], 'cuts': unit_group,
                          'source_start_sample': a, 'source_end_sample': b,
                          'minimum_frames': math.ceil((b - a) / FRAME_SAMPLES),
                          'baseline_minimum_frames': baseline_outer.get(unit_group[0]['id'], 0) if len(unit_group) == 1 else 0})
    assert units[0]['source_start_sample'] == 0 and units[-1]['source_end_sample'] == count
    assert all(a['source_end_sample'] == b['source_start_sample'] for a, b in zip(units, units[1:]))
    base_frames = sum(unit['minimum_frames'] for unit in units) + len(tasks) * TITLE_FRAMES + CARD_FRAMES
    assert base_frames <= MAX_FRAMES, f'Complete speech plus restored titles/card needs{base_frames/FPS:.6f}s>{MAX_FRAMES/FPS}s. No words or unreviewed quiet may be removed.'
    allocation, requested = allocate_readability(units, MAX_FRAMES - base_frames)
    entries, pieces, utterances, unit_proofs, sections = [], [], [], [], []
    cursor = 0
    current_section = None
    for unit, extra in zip(units, allocation):
        section_id = unit['section_id']
        section = by_section[section_id]
        if current_section != section_id:
            if sections:
                sections[-1].update(end_frame=cursor, end=cursor / FPS)
            sections.append({'id': section_id, 'section_id': section_id, 'type': section['type'],
                             'start_frame': cursor, 'start': cursor / FPS})
            current_section = section_id
            if section_id in tasks:
                entries.append({'section_id': section_id, 'kind': 'title', 'cut_id': None, 'cut_index': None,
                                'start_frame': cursor, 'end_frame': cursor + TITLE_FRAMES,
                                'start': cursor / FPS, 'end': (cursor + TITLE_FRAMES) / FPS, 'caption': ''})
                cursor += TITLE_FRAMES
        first_frame = cursor
        unit_frames = unit['minimum_frames'] + extra
        destination = first_frame * FRAME_SAMPLES
        source_a, source_b = unit['source_start_sample'], unit['source_end_sample']
        source_length = source_b - source_a
        piece = {'source_start_sample': source_a, 'source_end_sample': source_b,
                 'destination_start_sample': destination, 'destination_end_sample': destination + source_length,
                 'pcm_sha256': pcmsha(pcm[source_a * 2:source_b * 2]), 'section_id': section_id,
                 'cut_ids': [cut['id'] for cut in unit['cuts']], 'samples': source_length}
        pieces.append(piece)
        internal_frames = []
        for cut in unit['cuts'][:-1]:
            boundary = boundary_by_after[cut['id']]
            q = boundary['quiet']
            lo = destination + q['start_sample'] - source_a
            hi = destination + q['end_sample'] - source_a
            if 'current_master_review' in boundary:
                review_row = boundary['current_master_review']
                lo = max(lo, destination + review_row['actual_previous_speech_end_sample'] - source_a)
                hi = min(hi, destination + review_row['actual_next_speech_start_sample'] - source_a)
            else:
                lo = max(lo, destination + math.ceil(boundary['left_word_end'] * RATE) - source_a)
                hi = min(hi, destination + math.floor(boundary['right_word_start'] * RATE) - source_a)
            f0 = math.ceil((lo + .02 * RATE) / FRAME_SAMPLES)
            f1 = math.floor((hi - .02 * RATE) / FRAME_SAMPLES)
            assert f0 <= f1, f"No frame-safe current-wave boundary after{cut['id']}"
            wanted = round((destination + boundary['source_boundary_sample'] - source_a) / FRAME_SAMPLES)
            internal_frames.append(min(f1, max(f0, wanted)))
        frames = [first_frame] + internal_frames + [first_frame + unit_frames]
        assert all(a < b for a, b in zip(frames, frames[1:]))
        for index, cut in enumerate(unit['cuts']):
            f0, f1 = frames[index:index + 2]
            candidates = [i for i, source_cut in enumerate(section['cuts']) if source_cut.get('id') == cut['id']]
            assert len(candidates) == 1, f"Missing/duplicate physical spec cut: {cut['id']}"
            speech_a, speech_b = endpoints(cut, boundary_by_before.get(cut['id']), boundary_by_after.get(cut['id']), count)
            speech_dest_a = destination + speech_a - source_a
            speech_dest_b = destination + speech_b - source_a
            assert f0 * FRAME_SAMPLES <= speech_dest_a <= speech_dest_b <= f1 * FRAME_SAMPLES, f"Visual boundary cuts protected speech: {cut['id']}"
            entry = {'section_id': section_id, 'kind': 'cut', 'cut_id': cut['id'], 'cut_index': candidates[0],
                     'start_frame': f0, 'end_frame': f1, 'start': f0 / FPS, 'end': f1 / FPS,
                     'caption': cut['text']}
            entries.append(entry)
            utterances.append({'cut_id': cut['id'], 'id': cut['id'], 'section_id': section_id,
                               'text': cut['text'], 'spoken_text': cut['spoken_text'],
                               'source_start_sample': cut['source_start_sample'], 'source_end_sample': cut['source_end_sample'],
                               'source_protected_start_sample': speech_a, 'source_protected_end_sample': speech_b,
                               'source_protected_pcm_sha256': pcmsha(pcm[speech_a * 2:speech_b * 2]),
                               'destination_speech_start_sample': speech_dest_a, 'destination_speech_end_sample': speech_dest_b,
                               'destination_speech_start_seconds': speech_dest_a / RATE,
                               'destination_speech_end_seconds': speech_dest_b / RATE,
                               'visual_start_frame': f0, 'visual_end_frame': f1,
                               'raw_ASR_word_start': cut['word_start'], 'raw_ASR_word_end': cut['word_end'],
                               'first_word_index': cut['first_word_index'], 'last_word_index': cut['last_word_index'],
                               'all_protected_PCM_retained': True})
        unit_proofs.append({'section_id': section_id, 'cut_ids': piece['cut_ids'],
                            'source_start_sample': source_a, 'source_end_sample': source_b,
                            'audio_destination_start_sample': destination, 'audio_destination_end_sample': destination + source_length,
                            'visual_start_frame': first_frame, 'visual_end_frame': first_frame + unit_frames,
                            'minimum_frames': unit['minimum_frames'], 'baseline_minimum_frames': unit['baseline_minimum_frames'],
                            'readability_hold_frames': extra,
                            'frame_padding_samples': unit['minimum_frames'] * FRAME_SAMPLES - source_length})
        cursor += unit_frames
    card_start = cursor
    ending = by_section['ending']
    assert ending['cuts'][5]['id'] == 'ending_cut6'
    entries.append({'section_id': 'ending', 'kind': 'silent', 'cut_id': 'ending_cut6', 'cut_index': 5,
                    'start_frame': cursor, 'end_frame': cursor + CARD_FRAMES, 'start': cursor / FPS,
                    'end': (cursor + CARD_FRAMES) / FPS, 'caption': ''})
    cursor += CARD_FRAMES
    sections[-1].update(end_frame=cursor, end=cursor / FPS)
    assert len(entries) == 81 and len(utterances) == 68 and len(sections) == 14
    assert sum(entry['kind'] == 'title' for entry in entries) == 12
    assert entries[0]['start_frame'] == 0 and entries[-1]['end_frame'] == cursor <= MAX_FRAMES
    assert all(a['end_frame'] == b['start_frame'] for a, b in zip(entries, entries[1:]))
    assert sum(piece['samples'] for piece in pieces) == count
    assert all(a['source_end_sample'] == b['source_start_sample'] for a, b in zip(pieces, pieces[1:]))
    assert all(a['destination_end_sample'] <= b['destination_start_sample'] for a, b in zip(pieces, pieces[1:]))
    assert pieces[-1]['destination_end_sample'] <= card_start * FRAME_SAMPLES
    joined = b''.join(pcm[piece['source_start_sample'] * 2:piece['source_end_sample'] * 2] for piece in pieces)
    assert joined == pcm
    audio_segments = [{'file': alignment['master'], 'source_start_sample': piece['source_start_sample'],
                       'source_end_sample': piece['source_end_sample'], 'source_start': piece['source_start_sample'] / RATE,
                       'source_end': piece['source_end_sample'] / RATE, 'timeline_start_sample': piece['destination_start_sample'],
                       'timeline_end_sample': piece['destination_end_sample'], 'timeline_start': piece['destination_start_sample'] / RATE,
                       'timeline_end': piece['destination_end_sample'] / RATE, 'section_id': piece['section_id'],
                       'cut_ids': piece['cut_ids'], 'tempo_already_applied_to_master': 1.15,
                       'additional_tempo': 1, 'pcm_sha256': piece['pcm_sha256']} for piece in pieces]
    timing = {'status': 'PASS_TIMING_PROPOSAL' if args.analysis_only else 'PASS',
              'source_seconds': count / RATE, 'source_samples': count,
              'base_frames_including_restored_titles_and_card': base_frames,
              'base_seconds': base_frames / FPS, 'readability_budget_frames': MAX_FRAMES - base_frames,
              'baseline_outer_deficit_requested_frames': requested, 'allocated_outer_readability_frames': sum(allocation),
              'baseline_outer_minima_all_met': requested <= MAX_FRAMES - base_frames,
              'duration_seconds': cursor / FPS, 'frames': cursor, 'maximum_seconds': 330,
              'quiet_removed_samples': 0, 'all_fast_master_PCM_once': True,
              'added_padding_samples': cursor * FRAME_SAMPLES - count,
              'restored_title_frames': 720, 'final_card_frames': CARD_FRAMES,
              'outer_allocation_policy': 'Meet each baseline11 opening/ending spoken-cut minimum when possible; otherwise allocate available frames proportionally to those deficits. Never shorten source speech, remove quiet or alter1.15 tempo.',
              'units': unit_proofs}
    timeline = {'revision': 12, 'preview_only': bool(args.analysis_only), 'fps': FPS,
                'frames': cursor, 'duration': cursor / FPS, 'duration_seconds': cursor / FPS,
                'max_seconds': 330, 'allow_over_five_minutes': True, 'speech_tempo': 1.15, 'tempo': 1.15,
                'additional_tempo': 1, 'pitch_cents': 0,
                'generation_mode': 'two_part_with_user_authorization', 'two_part_exception_authorized': True,
                'source_identity_sha256': alignment['source_identity_sha256'],
                'source_voice_seconds': count / RATE, 'source_voice_samples': count,
                'source_voice_clock': 'Complete globally atempo1.15-processed master; source clocks never use old single-take or raw/1.15 approximations.',
                'final_card_seconds': 4, 'task_title_seconds': 2, 'task_title_count': 12,
                'entries': entries, 'sections': sections, 'audio_segments': audio_segments,
                'alignment': portable(args.alignment), 'alignment_sha256': sha(args.alignment),
                'completeness_review': review, 'placement_manifest': 'narration/placement-manifest.json',
                'timing_policy': timing}
    files = [Path(__file__), args.alignment, args.config, args.spec, args.baseline, source_path,
             rooted(alignment['source_descriptor']), rooted(alignment['tempo_provenance']['path']), ROOT / 'authorization.json']
    if args.completeness_review.exists():
        files.append(args.completeness_review)
    manifest = {'revision': 12, 'status': 'PROPOSAL_ONLY' if args.analysis_only else 'PASS_PCM_PLACEMENT',
                'production_timeline_committed': not args.analysis_only, 'source_identity_sha256': alignment['source_identity_sha256'],
                'generation_mode': 'two_part_with_user_authorization', 'default_generation_policy': 'single_take',
                'two_part_exception_authorized': True, 'source_parts': alignment['source_parts'],
                'composite_master': alignment['composite_master'], 'fast_master': alignment['fast_master'],
                'tempo_provenance': alignment['tempo_provenance'], 'speech_tempo': 1.15, 'additional_tempo': 1,
                'pitch_cents': 0, 'sample_rate': RATE, 'channels': 1,
                'working_sample_count': cursor * FRAME_SAMPLES, 'duration_seconds': cursor / FPS, 'frames': cursor,
                'retained_pieces': pieces, 'utterances': utterances,
                'boundaries': alignment['boundaries'], 'quiet_removals': [], 'quiet_removed_samples': 0,
                'spoken_samples_removed': 0, 'all_fast_master_samples_retained_once': True,
                'joined_retained_fast_PCM_sha256': pcmsha(joined), 'fast_master_pcm_sha256': pcmsha(pcm),
                'source_head_and_EOF_preserved': True, 'raw_sources_preserved_unmodified': True,
                'completeness_review': review, 'alignment': {'path': portable(args.alignment), 'sha256': sha(args.alignment)},
                'timing_policy': timing, 'audio_segments': audio_segments,
                'final_card_start_sample': card_start * FRAME_SAMPLES,
                'input_bindings': {portable(path): sha(path) for path in files},
                'scope': 'Exact retained fast-master pieces plus explicit zero-padding. No media generated or additional time/pitch processing. Raw-source PCM equality after the authorized1.15 tempo pass is not claimed.'}
    timing_output = ROOT / 'narration/timing-analysis.json'
    save(timing_output, timing)
    timeline_path = ROOT / 'narration/timeline-proposal.json' if args.analysis_only else args.timeline
    manifest_path = ROOT / 'narration/placement-proposal.json' if args.analysis_only else args.manifest
    save(timeline_path, timeline)
    manifest['timeline'] = {'path': portable(timeline_path), 'sha256': sha(timeline_path)}
    manifest['input_bindings'][portable(timeline_path)] = sha(timeline_path)
    save(manifest_path, manifest)
    return {'status': manifest['status'], 'frames': cursor, 'duration': cursor / FPS,
            'entries': len(entries), 'titles': 12, 'spoken': 68, 'quiet_removed_samples': 0,
            'baseline_outer_minima_all_met': timing['baseline_outer_minima_all_met'],
            'retained_pieces': len(pieces), 'timeline': portable(timeline_path), 'manifest': portable(manifest_path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment', type=Path, default=Path('narration/alignment.json'))
    parser.add_argument('--config', type=Path, default=Path('narration/ko.json'))
    parser.add_argument('--spec', type=Path, default=Path('spec.json'))
    parser.add_argument('--baseline', type=Path, default=Path('baseline/timeline-revision11.json'))
    parser.add_argument('--completeness-review', type=Path, default=Path('narration/completeness-review.json'))
    parser.add_argument('--timeline', type=Path, default=Path('timeline.json'))
    parser.add_argument('--manifest', type=Path, default=Path('narration/placement-manifest.json'))
    parser.add_argument('--analysis-only', action='store_true')
    args = parser.parse_args()
    for key in ['alignment', 'config', 'spec', 'baseline', 'completeness_review', 'timeline', 'manifest']:
        setattr(args, key, rooted(getattr(args, key)))
    sources = {path.resolve() for path in [args.alignment, args.config, args.spec, args.baseline, args.completeness_review, Path(__file__)]}
    assert args.timeline.suffix == args.manifest.suffix == '.json'
    assert args.timeline.resolve() != args.manifest.resolve() and not ({args.timeline.resolve(), args.manifest.resolve()} & sources)
    missing = [portable(path) for path in [args.alignment, args.config, args.spec, args.baseline] if not path.exists()]
    if missing:
        print(json.dumps({'status': 'PENDING_INPUTS', 'missing': missing, 'production_timeline_written': False}))
        return 2
    try:
        result = build(args)
    except Exception as exc:
        print(json.dumps({'status': 'BLOCKED', 'error': f'{type(exc).__name__}: {exc}',
                          'production_timeline_written': False}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
