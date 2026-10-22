#!/usr/bin/env python3
"""Audit the actual final MP4's local ASR against all approved utterances."""
from pathlib import Path
import hashlib, importlib.util, json, re

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / 'out/showcase-v12'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    sp = importlib.util.spec_from_file_location('current_alignment', ROOT / 'align.py')
    align = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(align)
    video = OUT / 'RD_Process_AI_Fast_Track_Showcase_Revision12.mp4'
    asr_path = OUT / 'final-transcription/RD_Process_AI_Fast_Track_Showcase_Revision12.json'
    asr = json.loads(asr_path.read_text())
    config = json.loads((ROOT / 'narration/ko.json').read_text())
    sources = json.loads((ROOT / 'narration/two-part-sources.json').read_text())
    mux = json.loads((OUT / 'mux-validation.json').read_text())
    aac = json.loads((OUT / 'encoded-audio-validation.json').read_text())
    coverage = json.loads((OUT / 'narration-coverage-validation.json').read_text())
    words = align.words_from(asr, 324.1333333333333)
    expected, spans = '', []
    for block in config['blocks']:
        for cut in block['cuts']:
            normalized, _ = align.normalize(cut['spoken_text'], config['pronunciation_map'])
            spans.append((block['section_id'], cut['id'], len(expected), len(expected) + len(normalized), cut))
            expected += normalized
    text, owners = '', []
    for i, word in enumerate(words):
        text += word['word']
        owners.extend([i] * len(word['word']))
    actual, actual_owners = align.normalize(text, config['pronunciation_map'], owners)
    mapping, matches, edits, distance = align.edit_align(expected, actual)
    rows = []
    for section, cut_id, start, end, cut in spans:
        mapped = [mapping[i] for i in range(start, end) if mapping[i] is not None]
        ids = [actual_owners[j] for j in mapped]
        first, last = min(ids), max(ids)
        ratio = sum(matches[start:end]) / (end - start)
        rows.append({'section_id': section, 'cut_id': cut_id, 'approved_text': cut['text'],
                     'ASR_start': words[first]['start'], 'ASR_end': words[last]['end'],
                     'ASR_text': ''.join(w['word'] for w in words[first:last + 1]).strip(),
                     'matched_character_ratio': ratio, 'ordered_lexical_anchor_present': ratio >= .72})
    compact = re.sub(r'\s+', '', asr['text'])
    patterns = {
        'RSAB15minutes_to1hour': r'15분에서1시간',
        'daily20minutes_to0': r'20분에서0분',
        'annual122hours': r'122시간',
        'TEM5minutes_to6seconds': r'5분에서6초',
        'Inline70percent': r'70(?:%|퍼센트)이상',
        'expense22indicators': r'22개판단지표',
        'Infra2hours40_to20min': r'2시간40분에서20분',
        'monitoring40percent': r'40(?:%|퍼센트)이상',
        'Cubic90percent': r'90(?:%|퍼센트)이상',
        'Plug1200to75seconds': r'1200초에서75초',
        'Plug317to19cases': r'317건에서19건',
    }
    figures = {name: bool(re.search(pattern, compact)) for name, pattern in patterns.items()}
    current_sha = sha(video)
    ending = [r for r in rows if r['section_id'] == 'ending']
    checks = {
        'actual_final_MP4_matches_mux_and_encoded_AAC_receipts': current_sha == mux['final_video_sha256'] == aac['final_video_sha256'],
        'all68_approved_lines_have_current_mix_lexical_anchors': len(rows) == 68 and all(r['ordered_lexical_anchor_present'] for r in rows),
        'all68_anchors_in_approved_order': all(a['ASR_start'] <= b['ASR_start'] for a, b in zip(rows, rows[1:])),
        'all_four_ending_lines_present': len(ending) == 4 and all(r['ordered_lexical_anchor_present'] for r in ending),
        'all11_critical_numeric_claims_present': all(figures.values()),
        'last_spoken_ending_finishes_before_final_card': ending[-1]['ASR_end'] <= 320.1333333333333,
        'complete_current_sources_already_independently_checked': coverage['sentences_complete'] == 68 and all(coverage['checks'].values()),
        'source_identity_is_current_two_part_master': sources['source_identity_sha256'] == coverage['source_identity_sha256'] == aac['source_identity_sha256'],
        'all14_final_AAC_regions_have_zero_sample_lag': len(aac['regions']) == 14 and all(r['best_lag_samples'] == 0 for r in aac['regions']),
        'all_encoded_AAC_core_checks_pass': all(aac['checks'].values()),
        'rejected_ro_teu_not_present_in_ASR': '로트' not in asr['text'],
    }
    assert all(checks.values()), checks
    result = {'revision': 12, 'status': 'PASS_WITH_ASR_VARIANTS', 'sentences_complete': 68,
              'final_video_sha256': current_sha, 'final_ASR_sha256': sha(asr_path),
              'source_identity_sha256': sources['source_identity_sha256'],
              'normalized_character_match_ratio': sum(matches) / len(matches),
              'global_edit_distance': distance, 'critical_numeric_checks': figures,
              'last_spoken_ending_end_seconds': ending[-1]['ASR_end'], 'checks': checks,
              'rows': rows, 'ASR_variants': 'Recognition writes 라트 for instructed 랏, 아이전트, technical spellings and minor particle/word variants. The approved script is not rewritten to match ASR; perfect pronunciation and subjective tone acceptance are not certified.',
              'scope': 'Local Whisper transcription of the actual final mixed-AAC MP4, ordered lexical coverage and11 figures, plus independently proven full-source completeness and encoded-AAC continuity. No new generation, waveform editing or subjective full-film listening.',
              'input_bindings': {str(p.relative_to(ROOT.parent)): sha(p) for p in [asr_path, ROOT / 'narration/ko.json', ROOT / 'narration/two-part-sources.json', OUT / 'narration-coverage-validation.json', OUT / 'mux-validation.json', OUT / 'encoded-audio-validation.json']}}
    (OUT / 'final-mix-narration-review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'sentences': 68, 'match_ratio': result['normalized_character_match_ratio'], 'minimum_line_match': min(r['matched_character_ratio'] for r in rows), 'checks': [sum(checks.values()), len(checks)]}))

if __name__ == '__main__':
    main()
