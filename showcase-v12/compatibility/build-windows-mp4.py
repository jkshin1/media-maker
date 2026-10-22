#!/usr/bin/env python3
"""Create a conservative MP4 derivative without modifying Revision12 or its AAC."""
from pathlib import Path
import hashlib, json, subprocess, datetime

SOURCE = Path(__file__).resolve().parents[1]
OUT = SOURCE.parent / 'out/showcase-v12'
TARGET = OUT / 'windows10'
INPUT = OUT / 'RD_Process_AI_Fast_Track_Showcase_Revision12.mp4'
EXPECTED_SHA = '8554cff5a71b81be36734c18a763f2aa94db36b3198d29984ac815325ffb972b'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def probe(path):
    return json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))

def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    assert sha(INPUT) == EXPECTED_SHA
    final = TARGET / 'RD_Process_AI_Fast_Track_Revision12_Windows10_Compatible.mp4'
    partial = final.with_suffix('.partial.mp4')
    command = ['ffmpeg', '-hide_banner', '-nostdin', '-y', '-i', str(INPUT),
               '-map', '0:v:0', '-map', '0:a:0', '-map_metadata', '-1', '-map_chapters', '-1', '-sn', '-dn',
               '-c:v', 'libx264', '-threads', '4', '-preset', 'fast', '-crf', '17',
               '-profile:v', 'baseline', '-level:v', '4.0', '-pix_fmt', 'yuv420p',
               '-refs', '1', '-bf', '0', '-g', '60', '-keyint_min', '60', '-sc_threshold', '0',
               '-x264-params', 'cabac=0:bframes=0:ref=1:weightp=0:8x8dct=0:open-gop=0:force-cfr=1',
               '-maxrate', '10M', '-bufsize', '20M', '-vf', 'setsar=1', '-r', '30', '-fps_mode', 'cfr',
               '-color_range', 'tv', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
               '-tag:v', 'avc1', '-video_track_timescale', '30000', '-c:a', 'copy',
               '-disposition:v:0', 'default', '-disposition:a:0', 'default',
               '-brand', 'mp42', '-movflags', '+faststart', str(partial)]
    with (TARGET / 'mp4-encode.log').open('w') as log:
        subprocess.run(command, check=True, stdout=log, stderr=log)
    result = probe(partial)
    video = next(s for s in result['streams'] if s['codec_type'] == 'video')
    audio = next(s for s in result['streams'] if s['codec_type'] == 'audio')
    assert video['codec_name'] == 'h264' and video['profile'] == 'Constrained Baseline' and video['level'] == 40
    assert video['width'] == 1920 and video['height'] == 1080 and video['pix_fmt'] == 'yuv420p'
    assert video['has_b_frames'] == 0 and video['r_frame_rate'] == '30/1' and int(video['nb_frames']) == 9724
    assert audio['codec_name'] == 'aac' and audio['profile'] == 'LC' and audio['sample_rate'] == '48000' and audio['channels'] == 2
    assert abs(float(result['format']['duration']) - 9724 / 30) < .001
    assert sha(INPUT) == EXPECTED_SHA
    partial.replace(final)
    receipt = {'status': 'ENCODE_COMPLETE_VALIDATION_PENDING', 'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'source': str(INPUT.relative_to(SOURCE.parent)), 'source_sha256': EXPECTED_SHA,
               'output': final.name, 'output_sha256': sha(final), 'bytes': final.stat().st_size,
               'command': command, 'probe': probe(final), 'audio_policy': 'Original AAC-LC packets copied; no voice, BGM, tempo, pitch, or gain change.',
               'video_policy': 'Only a codec transcode. Same1920x1080/30fps/9724frames and324.133333s; baseline, noBframes/CABAC/8x8transform/weightedP, one reference and2s closedGOP.',
               'windows_runtime': 'NOT_TESTED_ON_USER_WINDOWS10_PC'}
    (TARGET / 'mp4-build.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: receipt[k] for k in ['status', 'output', 'output_sha256', 'bytes']}))

if __name__ == '__main__':
    main()
