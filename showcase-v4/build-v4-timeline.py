#!/usr/bin/env python3
"""Allocate the four removed summaries to slower complete speech, at 9214 frames."""
from pathlib import Path
import hashlib, json, math

HERE = Path(__file__).resolve().parent
SR = 48000
FPS = 30
SPF = SR // FPS
TOTAL_FRAMES = 9214


def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def ceil_frames(samples): return math.ceil(samples / SPF - 1e-10)
def nearest_frames(samples): return math.floor(samples / SPF + .5)


def main():
    old = read(HERE / 'baseline-v3/timeline.json')
    spec = read(HERE / 'spec.json')
    mapping = read(HERE / 'narration/speech-edit-map-v4.json')
    provenance = read(HERE / 'narration/processed-continuous-v4-provenance.json')
    assert mapping['status'] in ['PASS', 'PASS_WITH_ASR_VARIANTS']
    assert len(spec['sections']) == 14 and not any(s['type'] == 'summary' for s in spec['sections'])
    assert mapping['processed_continuous']['sample_count'] == provenance['target_samples']
    assert provenance['target_samples'] - provenance['previous_processed_samples'] == 24 * SR
    cuts = {cut['cut_id']: cut for cut in mapping['cuts']}
    sections = {section['section_id']: section for section in mapping['sections']}
    assert len(cuts) == 73 and len(sections) == 14
    old_voice_entries = {entry['cut_id']: entry for entry in old['entries'] if entry.get('cut_id')}
    chunks = []
    for placement in old['audio_segments']:
        sid, cid = placement['section_id'], placement.get('cut_id')
        section = sections[sid]
        if cid:
            source_start = cuts[cid]['processed_start_sample']
            source_end = cuts[cid]['processed_end_sample']
            old_end = old_voice_entries[cid]['end_frame'] * SPF
            key = cid
        elif sid.startswith('task'):
            source_start, source_end = section['start_sample'], section['end_sample']
            old_end = max(e['end_frame'] for e in old['entries'] if e['section_id'] == sid) * SPF
            key = sid
        else:
            first = placement['source_start_sample'] == old['sections'][-1]['source_start_sample']
            split = cuts['ending_cut3']['safe_boundary_sample']
            source_start, source_end = (section['start_sample'], split) if first else (split, section['end_sample'])
            key = 'ending_first' if first else 'ending_last'
            old_end = old_voice_entries['ending_cut3' if first else 'ending_cut5']['end_frame'] * SPF
        old_gap = old_end - placement['timeline_start_sample'] - placement['sample_count']
        minimum = source_end - source_start
        if sid.startswith('task') or key == 'ending_last':
            minimum = max(minimum, section['actual_speech_end_sample'] - source_start + round(.23 * SR))
        chosen = max(ceil_frames(minimum), nearest_frames(source_end - source_start + old_gap))
        chunks.append({'key': key, 'section_id': sid, 'cut_id': cid,
                       'source_start_sample': source_start, 'source_end_sample': source_end,
                       'baseline_external_quiet_samples': old_gap, 'minimum_frames': ceil_frames(minimum),
                       'frames': chosen, 'initial_frames': chosen})
    # Frame rounding is paid only from the existing opening sentence pauses.
    # Task titles, ending gap, last card and every processed speech sample stay whole.
    fixed_frames = 12 * 60 + 30 + 120
    required_voice_frames = TOTAL_FRAMES - fixed_frames
    adjustment = required_voice_frames - sum(chunk['frames'] for chunk in chunks)
    opening_chunks = chunks[:9]
    remaining = adjustment
    while remaining:
        ranked = sorted(opening_chunks,
                        key=lambda chunk: chunk['frames'] * SPF - (chunk['source_end_sample'] - chunk['source_start_sample']),
                        reverse=remaining < 0)
        changed = False
        for chunk in ranked:
            if remaining < 0 and chunk['frames'] <= chunk['minimum_frames']:
                continue
            step = 1 if remaining > 0 else -1
            chunk['frames'] += step
            remaining -= step
            changed = True
            if remaining == 0:
                break
        assert changed, 'No existing opening quiet can cover frame rounding'
    assert sum(chunk['frames'] for chunk in chunks) == required_voice_frames
    chunk_by_key = {chunk['key']: chunk for chunk in chunks}
    entries, placements, section_records = [], [], []
    cursor = 0

    def add(original, count):
        nonlocal cursor
        assert count > 0
        entry = {**original, 'start_frame': cursor, 'end_frame': cursor + count,
                 'start': cursor / FPS, 'end': (cursor + count) / FPS,
                 'tempo': mapping['tempo_ratio']}
        if entry.get('cut_id'):
            cut = cuts[entry['cut_id']]
            entry['processed_source_start_sample'] = cut['processed_start_sample']
            entry['processed_source_end_sample'] = cut['processed_end_sample']
        entries.append(entry)
        cursor += count
        return entry

    def place(chunk):
        placements.append({'section_id': chunk['section_id'], 'cut_id': chunk['cut_id'],
                           'source_start_sample': chunk['source_start_sample'],
                           'source_end_sample': chunk['source_end_sample'],
                           'timeline_start_sample': cursor * SPF,
                           'sample_count': chunk['source_end_sample'] - chunk['source_start_sample']})

    for section in spec['sections']:
        sid = section['id']
        original = [entry for entry in old['entries'] if entry['section_id'] == sid]
        section_start = cursor
        info = sections[sid]
        if section['type'] == 'task':
            title = next(entry for entry in original if entry['kind'] == 'title')
            add(title, 60)
        body_start = cursor
        if section['type'] == 'opening':
            for entry in original:
                chunk = chunk_by_key[entry['cut_id']]
                place(chunk)
                add(entry, chunk['frames'])
        elif section['type'] == 'task':
            chunk = chunk_by_key[sid]
            place(chunk)
            for entry in [e for e in original if e['kind'] == 'cut']:
                if entry['cut_index'] == 4:
                    ending = body_start + chunk['frames']
                else:
                    ending = body_start + ceil_frames(cuts[entry['cut_id']]['safe_boundary_sample'] - info['start_sample'])
                add(entry, ending - cursor)
        else:
            for key, cut_ids in [('ending_first', ['ending_cut1', 'ending_cut2', 'ending_cut3']),
                                 ('ending_last', ['ending_cut5'])]:
                chunk = chunk_by_key[key]
                chunk_start = cursor
                place(chunk)
                for index, cid in enumerate(cut_ids):
                    entry = old_voice_entries[cid]
                    ending = chunk_start + (chunk['frames'] if index == len(cut_ids) - 1 else
                                            ceil_frames(cuts[cid]['safe_boundary_sample'] - chunk['source_start_sample']))
                    add(entry, ending - cursor)
                silent_index = 3 if key == 'ending_first' else 5
                silent = next(entry for entry in original if entry['kind'] == 'silent' and entry['cut_index'] == silent_index)
                add(silent, 30 if silent_index == 3 else 120)
        section_records.append({'section_id': sid, 'source_start_sample': info['start_sample'],
                                'source_end_sample': info['end_sample'], 'timeline_start_sample': body_start * SPF,
                                'timeline_end_sample': cursor * SPF, 'visual_section_start_frame': section_start,
                                'visual_section_end_frame': cursor})
    assert cursor == TOTAL_FRAMES and len(entries) == 87 and len(placements) == 23
    assert sum(entry['kind'] == 'cut' for entry in entries) == 73

    def convert(sample, sid, ending=False):
        candidates = [p for p in placements if p['section_id'] == sid and
                      (p['source_start_sample'] < sample <= p['source_end_sample'] if ending else
                       p['source_start_sample'] <= sample < p['source_end_sample'])]
        assert len(candidates) == 1, (sample, sid, ending)
        p = candidates[0]
        return p['timeline_start_sample'] + sample - p['source_start_sample']

    per_cut = []
    for entry in entries:
        if not entry.get('cut_id'):
            continue
        cut = cuts[entry['cut_id']]
        start = convert(cut['actual_speech_start_sample'], entry['section_id'])
        end = convert(cut['actual_speech_end_sample'], entry['section_id'], ending=True)
        margin = (entry['end_frame'] * SPF - end) / SR
        assert margin >= 0, (entry['cut_id'], 'previous phoneme exceeds visual boundary', margin)
        if entry['section_id'].startswith('task') and entry['cut_index'] == 4:
            assert margin >= .23, (entry['cut_id'], margin)
        per_cut.append({'cut_id': entry['cut_id'], 'section_id': entry['section_id'],
                        'actual_speech_start_sample': start, 'actual_speech_end_sample': end,
                        'visual_start_seconds': entry['start'], 'visual_end_seconds': entry['end'],
                        'tail_margin_seconds': margin,
                        'speech_start_before_visual_seconds': max(0, (entry['start_frame'] * SPF - start) / SR),
                        'boundary_confidence': cut['confidence']})
    for section in section_records:
        section['last_speech_end_sample'] = convert(sections[section['section_id']]['actual_speech_end_sample'], section['section_id'], ending=True)
    processed = {**mapping['processed_continuous'], 'path': 'narration/processed-continuous-v4.wav'}
    assert sha(HERE / processed['path']) == processed['sha256']
    result = {**old, 'duration': TOTAL_FRAMES / FPS, 'duration_seconds': TOTAL_FRAMES / FPS,
              'frames': TOTAL_FRAMES, 'fps': FPS, 'tempo': mapping['tempo_ratio'],
              'max_seconds': None, 'allow_over_five_minutes': True, 'entries': entries,
              'audio_segments': placements, 'sections': section_records,
              'source_voice_seconds': processed['duration_seconds'], 'fixed_silent_seconds': fixed_frames / FPS,
              'revision': {'revision': 4, 'four_summary_scenes_removed': True,
                           'removed_summary_seconds': 24, 'narration_extension_seconds': 24,
                           'approved_slower_narration': True, 'narration_captions': False,
                           'frame_budget_adjustment_from_opening_quiet_frames': adjustment,
                           'task_titles_seconds': 2, 'ending_silent_gap_seconds': 1,
                           'final_card_seconds': 4, 'user_allowed_over_five_minutes': True}}
    manifest = {'revision': 4, 'generation_mode': 'single_take',
                'source_master': mapping['source_master'], 'processed_master': processed,
                'tempo_ratio': mapping['tempo_ratio'], 'previous_tempo_ratio': provenance['previous_tempo_ratio'],
                'sample_rate': SR, 'placements': placements, 'sections': section_records,
                'per_cut_timing': per_cut, 'chunk_allocations': chunks,
                'speech_edit_map_sha256': sha(HERE / 'narration/speech-edit-map-v4.json'),
                'frames': TOTAL_FRAMES, 'duration': TOTAL_FRAMES / FPS,
                'processed_speech_extension_seconds': 24, 'audio_restarts_at_internal_task_cuts': False,
                'notes': ['Same complete original Kyung single take; one direct WSOLA processing pass at the approved slower factor.',
                          'All processed PCM is preserved exactly once in order. Only silence is inserted between selected complete paragraphs/sentences.',
                          'Four six-second summaries are removed. Twelve task titles, one-second ending gap and four-second final card retain their durations.',
                          'Frame rounding is balanced using the existing opening sentence quiet, without shortening speech or changing its speed.']}
    (HERE / 'timeline.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    (HERE / 'narration/revision-manifest-v4.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'frames': cursor, 'duration': cursor / FPS, 'entries': len(entries),
                      'speech_cuts': len(per_cut), 'pcm_placements': len(placements),
                      'opening_seconds': next(section['timeline_end_sample'] / SR for section in section_records if section['section_id'] == 'opening'),
                      'opening_frame_rounding_adjustment': adjustment,
                      'minimum_task_tail_margin': min(cut['tail_margin_seconds'] for cut in per_cut if cut['cut_id'].startswith('task') and cut['cut_id'].endswith('_cut5'))}, ensure_ascii=False))


if __name__ == '__main__':
    main()
