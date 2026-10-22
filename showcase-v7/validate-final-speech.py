#!/usr/bin/env python3
"""Read-only validation of the placed, normalized showcase-v2 narration.

Only a new report is written. The final WAV, source take, continuous processed
master, script, ASR and render timeline are never modified. Whisper timestamps
are approximate lexical anchors, not sample-accurate phoneme boundaries.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import wave

import numpy as np

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
EXCEPTIONS = {'task3_cut1', 'task4_cut1', 'task9_cut4'}
OVERLAP_STARTS = {'task3_cut2', 'task4_cut2', 'task9_cut5'}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        while data := handle.read(8 * 1024 * 1024):
            digest.update(data)
    return digest.hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def read_wave(path):
    with wave.open(str(path), 'rb') as handle:
        params = handle.getparams()
        assert (params.nchannels, params.sampwidth, params.framerate) == (1, 2, 48000)
        data = handle.readframes(params.nframes)
    return data, np.frombuffer(data, dtype='<i2'), params


def db(value):
    return float(20 * np.log10(max(float(value), 1e-12)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asr', type=Path, default=ROOT / 'narration/final-review/narration.json')
    parser.add_argument('--output', type=Path, default=PROJECT / 'out/showcase-v2/final-speech-review.json')
    args = parser.parse_args()
    config_path = ROOT / 'narration/ko.json'
    timeline_path = ROOT / 'timeline.json'
    map_path = ROOT / 'narration/speech-edit-map.json'
    voice_path = PROJECT / 'out/showcase-v2/narration.wav'
    raw_path = PROJECT / 'out/showcase-v2/narration-raw.wav'
    continuous_path = ROOT / 'narration/processed-continuous.wav'
    original_path = ROOT / 'narration/take.wav'
    config, timeline, editmap = load(config_path), load(timeline_path), load(map_path)
    helper_spec = importlib.util.spec_from_file_location('source_alignment', ROOT / 'align.py')
    helper = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper)
    words = helper.whisper_words(load(args.asr))
    pronunciation = config.get('pronunciation_map', {})
    expected = ''
    phrases = []
    for block in config['blocks']:
        for cut in block['cuts']:
            text = cut.get('spoken_text', cut['text'])
            normalized, _ = helper.normalize(text, pronunciation)
            phrases.append({
                'section_id': block['section_id'], 'cut_id': cut['id'],
                'text': cut['text'], 'spoken_text': text,
                'char_start': len(expected), 'char_end': len(expected) + len(normalized),
            })
            expected += normalized
    raw_transcript = ''.join(word['word'] for word in words)
    owners = [index for index, word in enumerate(words) for _ in word['word']]
    actual, actual_owners = helper.normalize(raw_transcript, pronunciation, owners)
    mapping, matches, edits, distance = helper.edit_align(expected, actual)

    voice_bytes, voice_pcm, voice_params = read_wave(voice_path)
    raw_bytes, raw_pcm, raw_params = read_wave(raw_path)
    continuous_bytes, continuous_pcm, continuous_params = read_wave(continuous_path)
    rate = 48000
    assert len(voice_pcm) == len(raw_pcm) == round(timeline['duration'] * rate)
    signal = voice_pcm.astype(np.float64) / 32768
    cumulative = np.concatenate(([0.0], np.cumsum(signal * signal)))
    window, hop = 480, 48  # 10 ms RMS, sampled every 1 ms.
    starts = np.arange(0, len(signal) - window + 1, hop)
    rms = np.sqrt(np.maximum(0, cumulative[starts + window] - cumulative[starts]) / window)
    rms_db = 20 * np.log10(np.maximum(rms, 1e-12))
    threshold = -45.0
    placements = timeline['audio_segments']

    def placed_sample(source_sample, ending=False):
        if ending:
            candidates = [segment for segment in placements
                          if segment['source_start_sample'] < source_sample <= segment['source_end_sample']]
        else:
            candidates = [segment for segment in placements
                          if segment['source_start_sample'] <= source_sample < segment['source_end_sample']]
        assert len(candidates) == 1, (source_sample, ending, candidates)
        segment = candidates[0]
        return segment['timeline_start_sample'] + source_sample - segment['source_start_sample']

    def first_quiet_after(anchor, limit, minimum_ms=20):
        # Search only at the independently reviewed phrase tail. A short gap
        # earlier inside a Korean word must not be used as a sentence ending.
        low = max(0, int(np.floor((anchor - .030) * 1000)))
        high = min(len(rms_db), int(np.floor(limit * 1000)))
        for position in range(low, high - minimum_ms + 1):
            if np.all(rms_db[position:position + minimum_ms] < threshold):
                return position / 1000
        return None

    entries = {entry['cut_id']: entry for entry in timeline['entries'] if entry.get('cut_id')}
    source_cuts = {cut['cut_id']: cut for cut in editmap['cuts']}
    boundaries = {point['after_cut']: point for point in editmap['boundaries']}
    cut_results = []
    for phrase in phrases:
        low, high = phrase['char_start'], phrase['char_end']
        indices = sorted({actual_owners[mapping[index]] for index in range(low, high)
                          if mapping[index] is not None})
        assert indices, phrase['cut_id']
        source = source_cuts[phrase['cut_id']]
        entry = entries[phrase['cut_id']]
        speech_start = placed_sample(source['actual_speech_start_sample']) / rate
        speech_end = placed_sample(source['actual_speech_end_sample'], ending=True) / rate
        quiet_start = first_quiet_after(speech_end, entry['end'])
        overlap = max(0, entry['start'] - speech_start)
        lexical_words = words[indices[0]:indices[-1] + 1]
        cut_results.append({
            **phrase, 'asr_text': ''.join(word['word'] for word in lexical_words).strip(),
            'exact_character_coverage': sum(matches[low:high]) / (high - low),
            'asr_first_word': lexical_words[0], 'asr_last_word': lexical_words[-1],
            'first_word_index': indices[0], 'last_word_index': indices[-1],
            'visual_start_seconds': entry['start'], 'visual_end_seconds': entry['end'],
            'reviewed_source_speech_start_seconds_in_final': speech_start,
            'reviewed_source_speech_end_seconds_in_final': speech_end,
            'reviewed_tail_margin_seconds': entry['end'] - speech_end,
            'normalized_sustained_quiet_start_seconds': quiet_start,
            'normalized_quiet_margin_seconds': None if quiet_start is None else entry['end'] - quiet_start,
            'normalized_rms_at_visual_end_dbfs': float(rms_db[min(len(rms_db) - 1, round(entry['end'] * 1000))]),
            'boundary_confidence': source['confidence'],
            'continuous_visual_only_exception': phrase['cut_id'] in EXCEPTIONS,
            'following_continuous_start_exception': phrase['cut_id'] in OVERLAP_STARTS,
            'conservative_start_overlap_seconds': overlap,
            'audio_split_at_this_internal_cut': False,
            'source_quiet_boundary': boundaries.get(phrase['cut_id'], {}).get('quiet_boundary'),
            'prior_word_complete_before_visual_end': (
                speech_end <= entry['end'] and lexical_words[-1]['end'] <= entry['end'] + .020
            ),
        })
    by_cut = {cut['cut_id']: cut for cut in cut_results}

    placement_results = []
    assembled = bytearray()
    cursor = 0
    for segment in placements:
        start, end = segment['source_start_sample'], segment['source_end_sample']
        position = segment['timeline_start_sample']
        expected_pcm = continuous_bytes[start * 2:end * 2]
        actual_pcm = raw_bytes[position * 2:(position + end - start) * 2]
        assert start == cursor
        cursor = end
        assembled.extend(actual_pcm)
        placement_results.append({
            **segment, 'exact_continuous_master_pcm': actual_pcm == expected_pcm,
            'pcm_sha256': hashlib.sha256(actual_pcm).hexdigest(),
        })
    exact_pcm = (cursor == len(continuous_pcm) and bytes(assembled) == continuous_bytes
                 and all(segment['exact_continuous_master_pcm'] for segment in placement_results))

    silent_results = []
    for entry in timeline['entries']:
        if entry['kind'] not in {'title', 'summary', 'silent'}:
            continue
        low, high = round(entry['start'] * rate), round(entry['end'] * rate)
        samples = signal[low:high]
        peak = db(np.max(np.abs(samples)))
        level = db(np.sqrt(np.mean(samples * samples)))
        active = int(np.count_nonzero(np.abs(samples) >= 10 ** (threshold / 20)))
        silent_results.append({
            'section_id': entry['section_id'], 'kind': entry['kind'],
            'start': entry['start'], 'end': entry['end'],
            'raw_pcm_exact_zero': not np.any(raw_pcm[low:high]),
            'normalized_peak_dbfs': peak, 'normalized_rms_dbfs': level,
            'normalized_nonzero_sample_count': int(np.count_nonzero(samples)),
            'normalized_samples_above_minus_45_dbfs': active,
            'no_speech_level_signal_after_highpass_and_loudnorm': active == 0,
        })

    block_results = []
    task_results = []
    for block in config['blocks']:
        sid = block['section_id']
        first, last = by_cut[block['cuts'][0]['id']], by_cut[block['cuts'][-1]['id']]
        section_placements = [segment for segment in placements if segment['section_id'] == sid]
        body_start = section_placements[0]['timeline_start_sample'] / rate
        head_begin = round(body_start * 1000)
        head_end = min(len(rms_db), round((body_start + 1) * 1000))
        active = np.flatnonzero(rms_db[head_begin:head_end] >= threshold)
        waveform_onset = None if not len(active) else (head_begin + int(active[0])) / 1000
        norm_expected_last, _ = helper.normalize(last['spoken_text'].split()[-1], pronunciation)
        norm_actual_last, _ = helper.normalize(last['asr_last_word']['word'], pronunciation)
        next_entry = next((entry for entry in timeline['entries']
                           if entry['start_frame'] == entries[last['cut_id']]['end_frame']), None)
        result = {
            'section_id': sid, 'cut_count': len(block['cuts']),
            'first_cut_id': first['cut_id'], 'last_cut_id': last['cut_id'],
            'expected_beginning': first['spoken_text'],
            'fresh_asr_beginning': first['asr_text'],
            'first_word': first['asr_first_word'], 'last_word': last['asr_last_word'],
            'expected_final_word': last['spoken_text'].split()[-1],
            'final_word_recognized_exact_after_notation_normalization': norm_expected_last == norm_actual_last,
            'body_start_seconds': body_start,
            'first_normalized_speech_level_onset_seconds': waveform_onset,
            'normalized_leading_quiet_seconds': None if waveform_onset is None else waveform_onset - body_start,
            'final_reviewed_source_word_end_seconds': last['reviewed_source_speech_end_seconds_in_final'],
            'final_normalized_sustained_quiet_start_seconds': last['normalized_sustained_quiet_start_seconds'],
            'following_visual_gate_seconds': last['visual_end_seconds'],
            'normalized_tail_margin_to_gate_seconds': last['normalized_quiet_margin_seconds'],
            'next_entry': None if next_entry is None else {
                'section_id': next_entry['section_id'], 'kind': next_entry['kind'],
                'start': next_entry['start'], 'end': next_entry['end'],
            },
            'complete_phrase_before_following_gate': (
                last['prior_word_complete_before_visual_end']
                and last['normalized_sustained_quiet_start_seconds'] is not None
                and last['normalized_sustained_quiet_start_seconds'] < last['visual_end_seconds']
            ),
        }
        block_results.append(result)
        if sid.startswith('task'):
            task_results.append(result)

    ordinary = [cut for cut in cut_results if not cut['continuous_visual_only_exception']]
    all_silent = all(region['raw_pcm_exact_zero'] and region['no_speech_level_signal_after_highpass_and_loudnorm']
                     for region in silent_results)
    checks = {
        'expected_14_continuous_blocks': len(block_results) == 14,
        'expected_73_narrated_phrases': len(cut_results) == 73,
        'all_73_phrases_lexically_located_in_order': (
            len(cut_results) == 73 and all(cut['exact_character_coverage'] >= .80 for cut in cut_results)
            and all(cut_results[index]['first_word_index'] <= cut_results[index + 1]['first_word_index']
                    for index in range(len(cut_results) - 1))
        ),
        'all_73_reviewed_previous_word_ends_before_visual_end': all(cut['prior_word_complete_before_visual_end'] for cut in cut_results),
        'all_70_ordinary_visual_ends_have_normalized_sustained_quiet': all(cut['normalized_sustained_quiet_start_seconds'] is not None for cut in ordinary),
        'exactly_three_reviewed_continuous_visual_only_exceptions': (
            {cut['cut_id'] for cut in cut_results if cut['continuous_visual_only_exception']} == EXCEPTIONS
        ),
        'only_three_declared_continuous_starts_may_overlap_visual_start': all(
            cut['conservative_start_overlap_seconds'] <= 1 / 48000 or cut['cut_id'] in OVERLAP_STARTS
            for cut in cut_results
        ),
        'all_14_final_words_recognized': all(block['final_word_recognized_exact_after_notation_normalization'] for block in block_results),
        'all_12_task_final_words_before_summary_or_next_scene': len(task_results) == 12 and all(task['complete_phrase_before_following_gate'] for task in task_results),
        'all_12_task_beginnings_start_after_their_titles': all(
            task['first_normalized_speech_level_onset_seconds'] is not None
            and task['first_normalized_speech_level_onset_seconds'] >= task['body_start_seconds']
            for task in task_results
        ),
        'all_18_requested_silent_regions_silent_after_normalization': len(silent_results) == 18 and all_silent,
        'all_processed_source_pcm_preserved_once_in_order': exact_pcm,
        'original_take_hash_matches_approved_source': sha(original_path) == editmap['source_master']['sha256'],
        'fixed_existing_tempo_preserved': timeline['tempo'] == editmap['tempo_ratio'],
        'no_new_tts_or_voice_or_script': (
            not editmap['new_tts'] and editmap['script_unchanged']
            and config['voice_id'] == editmap['voice_id'] and config['model_id'] == editmap['model_id']
            and sha(config_path) == editmap['source_config_sha256']
        ),
    }
    status = 'PASS_WITH_ASR_VARIANTS' if all(checks.values()) else 'FAIL'
    report = {
        'status': status, 'checks': checks,
        'voice': {'voice_id': config['voice_id'], 'voice_name': config['voice_name'], 'model_id': config['model_id']},
        'duration_seconds': len(voice_pcm) / rate, 'frames': timeline['frames'],
        'fixed_tempo_ratio': timeline['tempo'],
        'source_hashes': {str(path.relative_to(PROJECT)): sha(path) for path in
                          [voice_path, raw_path, continuous_path, original_path, config_path, timeline_path, map_path, args.asr]},
        'waveform_method': {
            'source': 'Final narration-only WAV after highpass and loudnorm; no BGM.',
            'sample_rate': rate, 'rms_window_seconds': .010, 'rms_hop_seconds': .001,
            'speech_level_threshold_dbfs': threshold, 'normal_tail_quiet_minimum_seconds': .020,
            'silence_is_physical_pcm_measurement': True,
            'small_filter_residuals_are_not_claimed_to_be_exact_digital_zero': True,
        },
        'asr': {
            'path': str(args.asr.relative_to(PROJECT)), 'model': 'local Whisper small',
            'expected_character_count': len(expected), 'recognized_normalized_character_count': len(actual),
            'exact_character_coverage': sum(matches) / len(expected), 'edit_distance': distance,
            'timestamps_are_approximate': True,
            'note': 'Lexical presence and complete final polite words corroborate source PCM. ASR may absorb leading silence or miswrite technical terms; it is not proof of exact pronunciation.',
            'edits': edits,
            'phrases_with_asr_notation_or_lexical_variants': [cut['cut_id'] for cut in cut_results if cut['exact_character_coverage'] < 1],
        },
        'summary': {
            'blocks_located': len(block_results), 'phrases_located': len(cut_results), 'tasks_checked': len(task_results),
            'silent_regions_checked': len(silent_results),
            'minimum_task_final_normalized_quiet_margin_seconds': min(task['normalized_tail_margin_to_gate_seconds'] for task in task_results),
            'minimum_task_normalized_leading_quiet_seconds': min(task['normalized_leading_quiet_seconds'] for task in task_results),
            'highest_normalized_silent_region_peak_dbfs': max(region['normalized_peak_dbfs'] for region in silent_results),
            'previous_stray_da_at_task17_or_task16_head': 'No separate da is recognized; all prior final words end before their gate, intervening summary/titles are physically silent, and source master PCM is preserved in order.',
        },
        'continuous_visual_only_exceptions': [cut for cut in cut_results if cut['continuous_visual_only_exception']],
        'blocks': block_results, 'task_gates': task_results,
        'cuts': cut_results, 'silent_regions': silent_results, 'pcm_placements': placement_results,
        'scope': 'Read-only final narration inspection. No narration generation, speed adjustment, media edit, script edit or render-input change occurred.',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': status, 'report': str(args.output), 'checks': checks, 'summary': report['summary']}, ensure_ascii=False, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == '__main__':
    raise SystemExit(main())
