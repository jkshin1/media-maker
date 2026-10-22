#!/usr/bin/env python3
"""Package completed Revision9 sources, assets and scoped validation records."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / 'out/showcase-v9'


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k != 'url' and not k.endswith('_url')}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def main():
    final = OUT / 'RD_Process_AI_Fast_Track_Showcase_Revision9.mp4'
    report = OUT / 'final-validation.json'
    assert final.exists() and report.exists(), 'The narrated final video is not complete; no final source package will be created.'
    validation = json.loads(report.read_text())
    assert validation['status'] == 'PASS'
    assert validation.get('final_sha256', validation.get('video_sha256')) == hashlib.sha256(final.read_bytes()).hexdigest()
    target = OUT / 'RD_Process_AI_Fast_Track_Showcase_Revision9_Source.zip'
    inventory = []
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(ROOT.rglob('*')):
            if not path.is_file() or any(p in {'node_modules', '__pycache__', '.DS_Store'} for p in path.relative_to(ROOT).parts):
                continue
            relative = str(path.relative_to(ROOT))
            data = path.read_bytes()
            if relative.startswith('narration/') and path.suffix == '.json' and any(k in path.name for k in ['receipt', 'generation']):
                data = (json.dumps(clean(json.loads(data)), ensure_ascii=False, indent=2) + '\n').encode()
            name = 'showcase-v9/' + relative
            z.writestr(name, data)
            inventory.append({'file': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
        receipts = ['SOURCE_STATUS.json', 'narration-script-review.json', 'generation-attempt-review.json',
                    'pipeline-synthetic-fixture-validation.json', 'visual-edit-validation.json',
                    'final-validation.json', 'render-validation.json', 'visual-validation.json',
                    'audio-validation.json', 'narration-coverage-validation.json', 'native-visual-review.json',
                    'encoded-visual-review.json', 'encoded-audio-validation.json', 'playback-validation.json',
                    'mux-validation.json', 'source-reproduction-validation.json',
                    'pause-edit-review.json', 'pause-plan-root-review.json', 'revision9-contract-review.json',
                    'incomplete-narration-review.json']
        for name in receipts:
            path = OUT / name
            if not path.exists():
                continue
            data = path.read_bytes()
            name = 'out/showcase-v9/' + name
            z.writestr(name, data)
            inventory.append({'file': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'kind': 'scoped_validation_receipt'})
        z.writestr('SOURCE_MANIFEST.json', json.dumps({'production_complete': True, 'delivery_status': 'FINAL',
            'revision': 9, 'max_seconds': 315,
            'generation_mode': 'single_take_with_authorized_original_ending_reuse',
            'ending_reuse_exception_authorized': True, 'speech_tempo': 1,
            'files': inventory, 'signed_generation_urls_omitted': True}, ensure_ascii=False, indent=2) + '\n')
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
    print(json.dumps({'file': str(target), 'bytes': target.stat().st_size,
                     'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'files': len(inventory)}))


if __name__ == '__main__':
    main()
