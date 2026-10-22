#!/usr/bin/env python3
"""Compare36 exact-frame samples to the delivered Revision12, without editing media."""
from pathlib import Path
import hashlib, json, re, subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / 'out/showcase-v12'
DEST = OUT / 'windows10'
FILM = DEST / 'RD_Process_AI_Fast_Track_Revision12_Windows10_Compatible.mp4'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    from PIL import Image, ImageDraw
    samples = json.loads((OUT / 'encoded-visual-review.json').read_text())['samples']
    assert len(samples) == 36
    original_sha = sha(OUT / 'RD_Process_AI_Fast_Track_Showcase_Revision12.mp4')
    before = sha(FILM)
    folder = DEST / 'visual-review'
    folder.mkdir(exist_ok=True)
    expression = '+'.join('eq(n,%d)' % r['frame_index'] for r in samples)
    command = ['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-threads', '2', '-i', str(FILM),
               '-map', '0:v:0', '-vf', 'select=' + expression.replace(',', r'\,'), '-fps_mode', 'vfr',
               '-y', str(folder / '%02d.png')]
    subprocess.run(command, check=True)
    refs = []
    for i, row in enumerate(samples, 1):
        reference = Path(row['file'])
        assert sha(reference) == row['sha256']
        refs.append("file '" + str(reference).replace("'", "'\\''") + "'\n")
    listing = folder / 'references.txt'
    listing.write_text(''.join(refs))
    stats = folder / 'ssim.txt'
    run = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(folder / '%02d.png'),
                          '-f', 'concat', '-safe', '0', '-i', str(listing),
                          '-lavfi', f'[0:v]setpts=N/(25*TB)[a];[1:v]setpts=N/(25*TB)[b];[a][b]ssim=stats_file={stats}',
                          '-an', '-f', 'null', '-'], capture_output=True, text=True, check=True)
    values = [float(v) for v in re.findall(r'All:([0-9.]+)', stats.read_text())]
    # The reference stills are an image concat, so verify exactly36 comparisons.
    assert len(values) == 36, (len(values), run.stderr)
    rows = []
    for i, (sample, value) in enumerate(zip(samples, values), 1):
        p = folder / f'{i:02d}.png'
        with Image.open(p) as image:
            assert image.size == (1920, 1080)
        rows.append({'sample_id': sample['sample_id'], 'frame_index': sample['frame_index'],
                     'file': str(p.relative_to(DEST)), 'sha256': sha(p), 'SSIM_to_original': value})
    contacts = []
    for group in range(3):
        sheet = Image.new('RGB', (960, 12 * 290), '#eeeeee')
        draw = ImageDraw.Draw(sheet)
        for j, i in enumerate(range(group * 12, min((group + 1) * 12, len(samples)))):
            with Image.open(samples[i]['file']) as image:
                sheet.paste(image.resize((480, 270)), (0, j * 290 + 20))
            with Image.open(folder / f'{i+1:02d}.png') as image:
                sheet.paste(image.resize((480, 270)), (480, j * 290 + 20))
            draw.text((5, j * 290 + 3), f"{i+1:02d} Original / Compatible  frame{samples[i]['frame_index']}", fill='black')
        p = folder / f'comparison-{group+1}.jpg'
        sheet.save(p, quality=90)
        contacts.append(str(p.relative_to(DEST)))
    checks = {'all36_exact_frame_samples': len(rows) == 36,
              'fullHD_dimensions_preserved': True,
              'all_samples_SSIM_above_point98': min(values) > .98,
              'original_and_compatible_media_unchanged': sha(FILM) == before and sha(OUT / 'RD_Process_AI_Fast_Track_Showcase_Revision12.mp4') == original_sha}
    result = {'status': 'PASS' if all(checks.values()) else 'FAIL', 'source_video_sha256': original_sha,
              'compatible_video_sha256': before, 'samples': rows, 'minimum_SSIM': min(values),
              'average_SSIM': sum(values) / len(values), 'checks': checks, 'contact_sheets': contacts,
              'scope': '36 exact-frame image comparisons including all12 titles,12 first photographs,8 result cards and opening/ending. Codec transcode quality/timing evidence; Windows Media Player runtime remains untested.'}
    (DEST / 'visual-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['status', 'minimum_SSIM', 'average_SSIM']}))
    assert all(checks.values()), checks

if __name__ == '__main__':
    main()
