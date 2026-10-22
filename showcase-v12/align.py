#!/usr/bin/env python3
"""Read-only, current-master alignment of the68 Revision12 utterances.

Default inputs are the newly authorized two-part complete1.15x master and its own
local Whisper word timestamps. Only an alignment JSON is written. No audio,
generation, pause edit, old timing map or production timeline is produced.
"""
from __future__ import annotations

import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import unicodedata
import wave

ROOT = Path(__file__).resolve().parent
RATE = 48000
EXPECTED_COUNTS = [9, 5, 5, 5, 4, 5, 5, 5, 3, 4, 4, 5, 5, 4]
ENDING_IDS = ['ending_cut1', 'ending_cut2', 'ending_cut3', 'ending_cut5']


def digest(data):
    return hashlib.sha256(data).hexdigest()


def rooted(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def portable(path):
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def normalize(text, pronunciation, owners=None):
    """Retain the proven character/word-owner map and notation aliases.

    Rejected 로트 is deliberately not normalized to the approved 랏.
    """
    chars, ids = [], []
    for i, char in enumerate(text):
        for output in unicodedata.normalize('NFKC', char).lower():
            if not output.isspace():
                chars.append(output)
                ids.append(owners[i] if owners is not None else i)
    value = ''.join(chars)
    aliases = dict(pronunciation)
    aliases.update({'CNC': '씨앤씨', '씨엔씨': '씨앤씨', 'SW': '에스더블유',
                    'MA': '엠에이', '아이전트': '에이전트', '써머리': '서머리',
                    '12개': '열두개', '십이개': '열두개', '1건': '한건',
                    '2시간': '두시간', '40분': '사십분', '20분': '이십분',
                    'PM': '피엠', 'K-파라미터': '케이파라미터', '1일': '일일',
                    '5개': '다섯개'})
    aliases = {source: target for source, target in aliases.items() if '로트' not in source}
    for source, target in sorted(aliases.items(), key=lambda pair: len(pair[0]), reverse=True):
        source = unicodedata.normalize('NFKC', source).lower().replace(' ', '')
        target = unicodedata.normalize('NFKC', target).lower().replace(' ', '')
        if not source or source == target:
            continue
        offset = 0
        while True:
            pos = value.find(source, offset)
            if pos < 0:
                break
            old = ids[pos:pos + len(source)]
            mapped = [old[min(len(old) - 1, int(i * len(old) / max(1, len(target))))] for i in range(len(target))]
            value = value[:pos] + target + value[pos + len(source):]
            ids = ids[:pos] + mapped + ids[pos + len(source):]
            offset = pos + len(target)
    keep = [i for i, char in enumerate(value) if char.isalnum()]
    return ''.join(value[i] for i in keep), [ids[i] for i in keep]


def edit_align(expected, actual):
    """Global Levenshtein traceback; every mapped char retains its word ID."""
    n, m = len(expected), len(actual)
    directions = bytearray((n + 1) * (m + 1))
    previous = array('H', range(m + 1))
    for j in range(1, m + 1):
        directions[j] = 2
    for i, a in enumerate(expected, 1):
        current = array('H', [i] + [0] * m)
        directions[i * (m + 1)] = 1
        for j, b in enumerate(actual, 1):
            choices = (previous[j - 1] + (a != b), previous[j] + 1, current[j - 1] + 1)
            cost = min(choices)
            current[j] = cost
            directions[i * (m + 1) + j] = choices.index(cost)
        previous = current
    mapping, matches, edits = [None] * n, [False] * n, []
    i, j = n, m
    while i or j:
        op = directions[i * (m + 1) + j]
        if i and j and op == 0:
            mapping[i - 1] = j - 1
            matches[i - 1] = expected[i - 1] == actual[j - 1]
            if not matches[i - 1]:
                edits.append({'kind': 'substitution', 'expected_index': i - 1,
                              'actual_index': j - 1, 'expected': expected[i - 1], 'actual': actual[j - 1]})
            i, j = i - 1, j - 1
        elif i and (not j or op == 1):
            edits.append({'kind': 'deletion', 'expected_index': i - 1,
                          'actual_index': j, 'expected': expected[i - 1]})
            i -= 1
        else:
            edits.append({'kind': 'insertion', 'expected_index': i,
                          'actual_index': j - 1, 'actual': actual[j - 1]})
            j -= 1
    return mapping, matches, list(reversed(edits)), int(previous[m])


def words_from(data, duration):
    source = data.get('words') or [word for segment in data.get('segments', []) for word in segment.get('words', [])]
    assert source, 'Current-master ASR word timestamps are required.'
    words = []
    for i, word in enumerate(source):
        start, end = float(word['start']), float(word['end'])
        assert math.isfinite(start) and math.isfinite(end) and 0 <= start <= end <= duration + .02
        words.append({'index': i, 'word': word.get('word', word.get('text', '')),
                      'start': start, 'end': end, 'start_sample': max(0, math.floor(start * RATE)),
                      'end_sample': min(round(duration * RATE), math.ceil(end * RATE)),
                      'probability': word.get('probability')})
    assert all(a['start'] <= b['start'] for a, b in zip(words, words[1:])), 'Unordered ASR words.'
    return words


def quiet_regions(pcm, threshold, minimum):
    import numpy as np
    samples = np.frombuffer(pcm, dtype='<i2').astype(np.float64) / 32768
    window = RATE // 100
    rms = np.sqrt(np.mean(samples[:len(samples) // window * window].reshape(-1, window) ** 2, axis=1))
    levels = 20 * np.log10(np.maximum(rms, 1e-15))
    rows, first = [], None
    for i, quiet in enumerate(list(levels < threshold) + [False]):
        if quiet and first is None:
            first = i
        if not quiet and first is not None:
            if (i - first) * .01 + 1e-9 >= minimum:
                rows.append({'start_sample': first * window, 'end_sample': i * window,
                             'start': first / 100, 'end': i / 100, 'duration': (i - first) / 100,
                             'peak_10ms_RMS_dbFS': float(max(levels[first:i]))})
            first = None
    return rows


def source_provenance(args, config, pcm, master_bytes):
    """Bind only the new pair, exact concatenation and whole-master tempo pass."""
    data_bytes = args.source_descriptor.read_bytes()
    descriptor = json.loads(data_bytes)
    assert descriptor['generation_mode'] == 'two_part_with_user_authorization'
    assert descriptor['speech_tempo'] == 1.15 and descriptor['pitch_cents'] == 0
    assert len(descriptor['parts']) == 2
    assert [len(part['cut_ids']) for part in descriptor['parts']] == [33, 35]
    ids = [cut['id'] for block in config['blocks'] for cut in block['cuts']]
    assert [cut_id for part in descriptor['parts'] for cut_id in part['cut_ids']] == ids
    assert descriptor['voice_id'] == config['voice_id'] and descriptor['model_id'] == config['model_id']
    payload = descriptor['source_identity_payload']
    identity = digest(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
    assert identity == descriptor['source_identity_sha256'], 'Two-part source identity is not canonical.'
    bindings = {portable(args.source_descriptor): digest(data_bytes)}
    authorization = descriptor['authorization']
    auth_path = rooted(authorization['path'])
    assert digest(auth_path.read_bytes()) == authorization['sha256']
    auth = json.loads(auth_path.read_text())
    assert auth['authorization_source'].startswith('direct_user')
    bindings[portable(auth_path)] = authorization['sha256']
    joined = hashlib.sha256()
    total = 0
    for part in descriptor['parts']:
        path = rooted(part['master'])
        assert digest(path.read_bytes()) == part['master_sha256']
        with wave.open(str(path)) as w:
            assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (RATE, 1, 2)
            content = w.readframes(w.getnframes())
        assert digest(content) == part['master_pcm_sha256']
        assert len(content) // 2 == part['samples']
        assert part['virtual_start_sample'] == total
        total += part['samples']
        assert part['virtual_end_sample'] == total
        joined.update(content)
        bindings[portable(path)] = part['master_sha256']
        prompt = rooted(part['prompt_file'])
        assert digest(prompt.read_bytes()) == part['prompt_sha256']
        bindings[portable(prompt)] = part['prompt_sha256']
    composite = descriptor['composite_master']
    composite_path = rooted(composite['path'])
    assert digest(composite_path.read_bytes()) == composite['sha256']
    with wave.open(str(composite_path)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (RATE, 1, 2)
        composite_pcm = w.readframes(w.getnframes())
    assert total == composite['samples'] == len(composite_pcm) // 2
    assert joined.hexdigest() == composite['pcm_sha256'] == digest(composite_pcm)
    fast = descriptor['fast_master']
    assert rooted(fast['path']).resolve() == args.master.resolve()
    assert digest(master_bytes) == fast['sha256'] and digest(pcm) == fast['pcm_sha256']
    assert len(pcm) // 2 == fast['samples']
    tempo = descriptor['tempo_provenance']
    tempo_path = rooted(tempo['path'])
    assert digest(tempo_path.read_bytes()) == tempo['sha256']
    tempo_data = json.loads(tempo_path.read_text())
    assert tempo_data['filter'] == 'atempo=1.15' and tempo_data['continuous_master_processing'] is True
    assert tempo_data['speech_tempo_requested'] == 1.15 and tempo_data['pitch_cents'] == 0
    assert tempo_data['source_sha256'] == composite['sha256'] and tempo_data['output_sha256'] == fast['sha256']
    assert tempo_data['source_samples'] == total and tempo_data['output_samples'] == len(pcm) // 2
    bindings.update({portable(composite_path): composite['sha256'], portable(tempo_path): tempo['sha256']})
    return {'generation_mode': descriptor['generation_mode'], 'source_identity_sha256': identity,
            'source_parts': descriptor['parts'], 'composite_master': composite,
            'fast_master': fast, 'tempo_provenance': tempo,
            'two_part_authorization': authorization,
            'two_raw_sources_exactly_concatenated': True,
            'source_identity_payload': payload,
            'source_descriptor': portable(args.source_descriptor),
            'source_descriptor_sha256': digest(data_bytes), 'bindings': bindings}


def overlapping_words(words, point):
    return [word['index'] for word in words if word['start_sample'] < point < word['end_sample']]


def boundary(left, right, words, quiet, fps, min_quiet, margin, review=None):
    row = {'after_cut': left['id'], 'before_cut': right['id'],
           'section_boundary': left['section_id'] != right['section_id'],
           'status': 'REVIEW_REQUIRED_MISSING_LEXICAL_ANCHOR', 'source_boundary_sample': None,
           'proposed_source_boundary_sample': None, 'independently_reviewed': False}
    if left['word_end'] is None or right['word_start'] is None:
        return row
    lo, hi = left['word_end'], right['word_start']
    center = (lo + hi) / 2
    row.update(left_word_end=lo, right_word_start=hi, lexical_gap_seconds=hi - lo,
               left_last_word_index=left['last_word_index'], right_first_word_index=right['first_word_index'])
    if review is not None:
        point = int(review['source_boundary_sample'])
        previous_end = int(review['actual_previous_speech_end_sample'])
        next_start = int(review['actual_next_speech_start_sample'])
        assert review.get('evidence'), 'Current-master boundary review needs evidence.'
        regions = [q for q in quiet if q['start_sample'] < point < q['end_sample']]
        assert regions and previous_end <= point <= next_start, 'Review point is not inside current-wave quiet/speech endpoints.'
        q = max(regions, key=lambda item: item['duration'])
        assert point - q['start_sample'] >= round(margin * RATE) and q['end_sample'] - point >= round(margin * RATE)
        row.update(status='REVIEWED_CURRENT_MASTER_WORD_WAVE', source_boundary_sample=point,
                   source_boundary_seconds=point / RATE, quiet=q, evidence=review['evidence'],
                   independently_reviewed=bool(review.get('independently_reviewed', False)),
                   explicit_current_master_review_used=True, current_master_review=review,
                   original_ASR_words_overlapping_point=overlapping_words(words, point),
                   basis='Explicit current-master/current-ASR endpoint review plus measured sustained quiet; approximate ASR ownership preserved as evidence.')
        return row
    candidates = []
    if left['last_word_index'] < right['first_word_index']:
        for q in quiet:
            a, b = max(lo, q['start']), min(hi, q['end'])
            if b - a + 1e-9 < min_quiet:
                continue
            f0 = math.ceil((a + margin) * fps - 1e-8)
            f1 = math.floor((b - margin) * fps + 1e-8)
            if f0 > f1:
                continue
            frame = min(f1, max(f0, round((a + b) / 2 * fps)))
            point = round(frame * RATE / fps)
            if overlapping_words(words, point):
                continue
            candidates.append((abs(point / RATE - center), point, frame, q, a, b))
    if candidates:
        _, point, frame, q, a, b = min(candidates, key=lambda item: item[0])
        row.update(status='WORD_WAVE_SAFE', source_boundary_sample=point,
                   source_boundary_seconds=point / RATE, source_clock_frame=frame, quiet=q,
                   lexical_quiet_intersection_seconds=[a, b], ASR_words_overlapping_point=[],
                   quiet_before_seconds=(point - q['start_sample']) / RATE,
                   quiet_after_seconds=(q['end_sample'] - point) / RATE,
                   basis='Sustained current waveform quiet inside the ordered lexical phrase gap; frame point has quiet margin and intersects no ASR word.')
        return row
    # Evidence-only candidates never become source segment boundaries.
    nearby = []
    last_word, next_word = words[left['last_word_index']], words[right['first_word_index']]
    for q in quiet:
        mid = (q['start'] + q['end']) / 2
        if q['start'] > last_word['start'] + .04 and q['end'] < next_word['end'] - .02 and abs(mid - center) < 2:
            nearby.append((abs(mid - center), q))
    if nearby:
        _, q = min(nearby, key=lambda item: item[0])
        point = (q['start_sample'] + q['end_sample']) // 2
        row.update(status='REVIEW_REQUIRED_ASR_PAUSE_ATTRIBUTION', candidate_quiet=q,
                   proposed_source_boundary_sample=point,
                   candidate_ASR_words_overlapping_point=overlapping_words(words, point),
                   basis='Wave quiet may be assigned to a preceding/next ASR word. Regional phonetic/ASR review is required; candidate was not accepted.')
    else:
        row.update(status='REVIEW_REQUIRED_NO_WORD_WAVE_GAP',
                   basis='No sustained quiet inside the lexical phrase gap. Do not use low signal inside a Korean word or reuse an old exception.')
    return row


def align(args):
    config_bytes, master_bytes, asr_bytes = args.config.read_bytes(), args.master.read_bytes(), args.asr.read_bytes()
    config, transcript = json.loads(config_bytes), json.loads(asr_bytes)
    assert [len(block['cuts']) for block in config['blocks']] == EXPECTED_COUNTS
    flat = [dict(cut, section_id=block['section_id']) for block in config['blocks'] for cut in block['cuts']]
    assert len(flat) == len({cut['id'] for cut in flat}) == 68
    assert [cut['id'] for cut in flat[-4:]] == ENDING_IDS
    with wave.open(str(args.master)) as source:
        assert (source.getframerate(), source.getnchannels(), source.getsampwidth(), source.getcomptype()) == (RATE, 1, 2, 'NONE')
        count = source.getnframes()
        pcm = source.readframes(count)
    assert len(pcm) == count * 2 and count > 0
    source_info = source_provenance(args, config, pcm, master_bytes)
    duration = count / RATE
    words = words_from(transcript, duration)
    expected, cuts = '', []
    aliases = config.get('pronunciation_map', {})
    for cut in flat:
        normalized, _ = normalize(cut['spoken_text'], aliases)
        cuts.append(dict(cut, normalized_spoken_text=normalized, char_start=len(expected), char_end=len(expected) + len(normalized)))
        expected += normalized
    raw, owners = '', []
    for i, word in enumerate(words):
        raw += word['word']
        owners.extend([i] * len(word['word']))
    actual, word_owners = normalize(raw, aliases, owners)
    mapping, matches, edits, distance = edit_align(expected, actual)
    for cut in cuts:
        a, b = cut['char_start'], cut['char_end']
        mapped = [mapping[i] for i in range(a, b) if mapping[i] is not None]
        cut.update(character_coverage=sum(matches[a:b]) / (b - a), first_word_index=None,
                   last_word_index=None, first_word=None, last_word=None,
                   word_start=None, word_end=None, word_start_sample=None,
                   word_end_sample=None, asr_text='')
        if mapped:
            first, last = min(word_owners[i] for i in mapped), max(word_owners[i] for i in mapped)
            cut.update(first_word_index=first, last_word_index=last, word_start=words[first]['start'],
                       word_end=words[last]['end'], first_word=words[first]['word'], last_word=words[last]['word'],
                       word_start_sample=words[first]['start_sample'], word_end_sample=words[last]['end_sample'],
                       asr_text=' '.join(w['word'].strip() for w in words[first:last + 1]))
        cut['lexical_anchor_pass'] = bool(cut['word_start'] is not None and cut['character_coverage'] >= args.cut_coverage_min)
        cut['ASR_variant_requires_independent_review'] = cut['character_coverage'] < 1
        cut['raw_ASR_Lot_variants'] = [w for w in words[(cut['first_word_index'] or 0):(cut['last_word_index'] + 1 if cut['last_word_index'] is not None else 0)] if any(form in w['word'] for form in ['랏', '로트', '라트', 'LAT', '낫', '낮'])]
    quiet = quiet_regions(pcm, args.quiet_dbfs, args.minimum_quiet_seconds)
    review_rows, review_binding = {}, {}
    if args.reviews:
        review_bytes = args.reviews.read_bytes()
        reviews = json.loads(review_bytes)
        assert reviews['master_sha256'] == digest(master_bytes) and reviews['asr_sha256'] == digest(asr_bytes), 'Boundary review belongs to another master/ASR.'
        review_rows = {(row['after_cut'], row['before_cut']): row for row in reviews.get('boundaries', [])}
        review_binding = {portable(args.reviews): digest(review_bytes)}
    boundaries = [boundary(a, b, words, quiet, args.fps, args.minimum_quiet_seconds,
                           args.boundary_quiet_margin_seconds, review_rows.get((a['id'], b['id'])))
                  for a, b in zip(cuts, cuts[1:])]
    points = [0] + [row['source_boundary_sample'] for row in boundaries] + [count]
    partition_possible = all(point is not None for point in points)
    partition_ordered = partition_possible and all(a < b for a, b in zip(points, points[1:]))
    joined_hash = hashlib.sha256()
    for i, cut in enumerate(cuts):
        start, end = points[i:i + 2]
        confirmed = start is not None and end is not None and start < end
        cut.update(source_start_sample=start if confirmed else None, source_end_sample=end if confirmed else None,
                   source_start=start / RATE if confirmed else None, source_end=end / RATE if confirmed else None,
                   source_segment_confirmed=confirmed, source_pcm_sha256=None)
        if confirmed:
            content = pcm[start * 2:end * 2]
            cut.update(source_samples=end - start, source_seconds=(end - start) / RATE, source_pcm_sha256=digest(content))
            if partition_ordered:
                joined_hash.update(content)
        cut['status'] = ('LEXICALLY_ANCHORED_SEGMENT_WORD_WAVE_SAFE' if confirmed and cut['lexical_anchor_pass']
                         else 'REVIEW_REQUIRED')
    segments_exact = bool(partition_ordered and joined_hash.hexdigest() == digest(pcm))
    blocks = []
    for block in config['blocks']:
        group = [cut for cut in cuts if cut['section_id'] == block['section_id']]
        a, b = group[0]['source_start_sample'], group[-1]['source_end_sample']
        blocks.append({'section_id': block['section_id'], 'cut_ids': [cut['id'] for cut in group],
                       'source_start_sample': a, 'source_end_sample': b,
                       'source_pcm_sha256': digest(pcm[a * 2:b * 2]) if a is not None and b is not None and a < b else None})
    coverage = sum(matches) / len(expected)
    ordered = all(a['last_word_index'] is not None and b['first_word_index'] is not None and a['last_word_index'] < b['first_word_index'] for a, b in zip(cuts, cuts[1:]))
    lexical = coverage >= args.coverage_min and all(cut['lexical_anchor_pass'] for cut in cuts)
    ending = [cut for cut in cuts if cut['section_id'] == 'ending']
    last_asr, _ = normalize(ending[-1]['asr_text'], aliases)
    ending_gate = all(cut['lexical_anchor_pass'] for cut in ending) and '만나봅니다' in last_asr
    safe_count = sum(row['source_boundary_sample'] is not None for row in boundaries)
    automatic = lexical and ordered and ending_gate and safe_count == 67 and segments_exact
    auth_path = ROOT / 'authorization.json'
    auth_binding = {}
    if auth_path.exists():
        auth_bytes = auth_path.read_bytes()
        auth = json.loads(auth_bytes)
        assert auth['script_lines'] == 68
        assert auth['speech_tempo'] == 1.15 and auth['pitch_cents'] == 0 and auth['max_video_seconds'] == 330
        assert digest(config['generated_prompt'].encode()) == auth['script_sha256'], 'Config prompt differs from Revision12 authorization.'
        auth_binding[portable(auth_path)] = digest(auth_bytes)
    return {
        'revision': 12, 'status': 'READY_FOR_INDEPENDENT_REVIEW' if automatic else 'REVIEW_REQUIRED',
        'analysis_only': True, 'production_ready': False, 'ready_for_timeline_review': bool(automatic),
        'scope': 'Current processed continuous master only. Algorithmic lexical anchors and word/wave boundaries are evidence; independent completeness/ASR-variant review remains required. No media or production timeline was changed.',
        'generation_mode': source_info['generation_mode'],
        'source_identity_sha256': source_info['source_identity_sha256'],
        'source_parts': source_info['source_parts'], 'source_descriptor': source_info['source_descriptor'],
        'source_descriptor_sha256': source_info['source_descriptor_sha256'],
        'composite_master': source_info['composite_master'], 'fast_master': source_info['fast_master'],
        'tempo_provenance': source_info['tempo_provenance'],
        'two_part_authorization': source_info['two_part_authorization'],
        'two_raw_sources_exactly_concatenated': True,
        'default_generation_policy': 'single_take', 'two_part_exception_authorized': True,
        'speech_tempo_requested': 1.15, 'pitch_cents_requested': 0,
        'input_master_role': 'Global pitch-preserving1.15x complete master, not per-cut audio restarts',
        'tempo_processing_verified_by_this_aligner': False, 'maximum_video_seconds_authorized': 330,
        'bound_whole_master_tempo_provenance_verified': True,
        'full_video_duration_cap_checked': False, 'titles_and_final_card_timing_owned_by_timeline_builder': True,
        'master': portable(args.master), 'master_sha256': digest(master_bytes), 'master_pcm_sha256': digest(pcm),
        'master_samples': count, 'master_seconds': duration, 'sample_rate': RATE, 'channels': 1, 'sample_width': 2,
        'asr': portable(args.asr), 'asr_sha256': digest(asr_bytes), 'config': portable(args.config),
        'config_sha256': digest(config_bytes), 'generated_prompt_sha256': digest(config['generated_prompt'].encode()),
        'sentence_count': 68, 'block_count': 14, 'boundary_count': 67, 'safe_boundary_count': safe_count,
        'lexically_anchored_sentence_count': sum(cut['lexical_anchor_pass'] for cut in cuts),
        'ending_sentence_count': len(ending), 'ending_lexical_gate_pass': bool(ending_gate),
        'ending_final_anchor': '만나봅니다', 'exact_character_coverage': coverage, 'edit_distance': distance,
        'lexical_gate_pass': bool(lexical), 'ordered_word_anchors_pass': bool(ordered),
        'all67_word_waveform_boundaries_confirmed': safe_count == 67,
        'all68_contiguous_segments_cover_master0_to_EOF_exact': segments_exact,
        'joined_segment_pcm_sha256': joined_hash.hexdigest() if partition_ordered else None,
        'master_head_preserved': cuts[0]['source_start_sample'] == 0,
        'master_EOF_preserved': cuts[-1]['source_end_sample'] == count,
        'source_samples_removed': 0, 'source_samples_duplicated': 0, 'audio_files_written': 0,
        'quiet_threshold_dbFS': args.quiet_dbfs, 'RMS_window_seconds': .01,
        'minimum_sustained_quiet_seconds': args.minimum_quiet_seconds,
        'boundary_quiet_margin_each_side_seconds': args.boundary_quiet_margin_seconds,
        'source_clock_fps_for_safe_boundary_candidates': args.fps,
        'cuts': cuts, 'blocks': blocks, 'boundaries': boundaries, 'words': words, 'quiet_regions': quiet,
        'edits': edits, 'ending_cuts': ending,
        'review_required_cut_ids': [cut['id'] for cut in cuts if not cut['lexical_anchor_pass'] or not cut['source_segment_confirmed'] or cut['ASR_variant_requires_independent_review']],
        'review_required_boundaries': [row for row in boundaries if row['source_boundary_sample'] is None],
        'normalization': 'Saved notation/number aliases, whitespace and punctuation only. Rejected 로트 and raw 랏 variants remain distinct; ASR spelling is not literal pronunciation proof.',
        'input_bindings': {portable(args.master): digest(master_bytes), portable(args.asr): digest(asr_bytes),
                           portable(args.config): digest(config_bytes), portable(Path(__file__)): digest(Path(__file__).read_bytes()),
                           **source_info['bindings'], **auth_binding, **review_binding},
        'limitations': ['No provider completion record or prompt match alone proves all68 utterances were spoken.',
                       'ASR word timestamps are approximate; unconfirmed leading-pause attribution stays REVIEW.',
                       'A low-energy interval inside a Korean word is not an accepted sentence boundary.',
                       'Every source segment uses the processed-master sample clock, not raw timestamps divided by1.15.',
                       'No human listening, exact pronunciation, preferred-tone match or final330-second film PASS is claimed.'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--master', type=Path, default=Path('narration/elevenlabs/complete-tempo1.15.wav'))
    parser.add_argument('--asr', type=Path, default=Path('narration/transcription/complete-tempo1.15.json'))
    parser.add_argument('--config', type=Path, default=Path('narration/ko.json'))
    parser.add_argument('--source-descriptor', type=Path, default=Path('narration/two-part-sources.json'))
    parser.add_argument('--output', '--out', type=Path, default=Path('narration/alignment.json'))
    parser.add_argument('--reviews', type=Path, help='Optional current-master/current-ASR SHA-bound endpoint evidence JSON.')
    parser.add_argument('--coverage-min', type=float, default=.92)
    parser.add_argument('--cut-coverage-min', type=float, default=.80)
    parser.add_argument('--quiet-dbfs', type=float, default=-48)
    parser.add_argument('--minimum-quiet-seconds', type=float, default=.08)
    parser.add_argument('--boundary-quiet-margin-seconds', type=float, default=.02)
    parser.add_argument('--fps', type=int, default=30)
    args = parser.parse_args()
    for name in ['master', 'asr', 'config', 'source_descriptor', 'output', 'reviews']:
        if getattr(args, name) is not None:
            setattr(args, name, rooted(getattr(args, name)))
    assert args.output.suffix.lower() == '.json', 'The only allowed output is an alignment JSON report.'
    protected = [args.master, args.asr, args.config, args.source_descriptor, ROOT / 'authorization.json', Path(__file__)]
    if args.reviews:
        protected.append(args.reviews)
    assert args.output.resolve() not in {path.resolve() for path in protected}, 'Never overwrite an input, source, review or audio file.'
    assert args.minimum_quiet_seconds >= .08 and args.boundary_quiet_margin_seconds >= .02
    assert args.fps > 0 and 0 < args.cut_coverage_min <= args.coverage_min <= 1
    missing = [portable(path) for path in [args.master, args.asr, args.config, args.source_descriptor] if not path.exists()]
    if missing:
        print(json.dumps({'status': 'PENDING_INPUTS', 'missing': missing, 'alignment_written': False}))
        return 2
    try:
        report = align(args)
    except Exception as exc:
        report = {'revision': 12, 'status': 'FAIL_INPUT_OR_ALIGNMENT', 'analysis_only': True,
                  'production_ready': False, 'audio_files_written': 0,
                  'error': f'{type(exc).__name__}: {exc}'}
        save(args.output, report)
        print(json.dumps(report, ensure_ascii=False))
        return 1
    save(args.output, report)
    print(json.dumps({key: report[key] for key in ['status', 'sentence_count', 'safe_boundary_count',
                     'lexically_anchored_sentence_count', 'ending_lexical_gate_pass',
                     'exact_character_coverage', 'master_seconds',
                     'all68_contiguous_segments_cover_master0_to_EOF_exact']}, ensure_ascii=False))
    return 0 if report['ready_for_timeline_review'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
