#!/usr/bin/env python3
"""Decode and verify the delivered opening using Python stdlib plus FFmpeg."""
import hashlib,json,os,subprocess
from pathlib import Path
BASE=Path(__file__).resolve().parent
OUT=Path(os.environ.get('OPENING_OUT',BASE.parent/'out'/'opening-v2')).resolve()
FINAL=OUT/'rd-ai-fast-track-opening-v2.mp4'
def run(args):
    return subprocess.run(args,check=True,capture_output=True,text=True).stdout
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
meta=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(FINAL)]))
v=next(s for s in meta['streams'] if s['codec_type']=='video')
a=next(s for s in meta['streams'] if s['codec_type']=='audio')
assert (v['width'],v['height'],v['r_frame_rate'],v['codec_name'],v['pix_fmt'])==(1920,1080,'30/1','h264','yuv420p')
assert int(v['nb_frames'])==1380
assert abs(float(meta['format']['duration'])-46)<1/30
assert a['codec_name']=='aac' and int(a['sample_rate'])==48000
run(['ffmpeg','-v','error','-i',str(FINAL),'-f','null','-'])
def video_hash(file):
    return run(['ffmpeg','-v','error','-i',str(file),'-map','0:v:0','-c:v','copy','-f','hash','-hash','sha256','-']).strip()
original_hash=video_hash(OUT/'video_silent.mp4');final_hash=video_hash(FINAL)
assert original_hash==final_hash,'Video packets changed during audio mux'
black=subprocess.run(['ffmpeg','-hide_banner','-i',str(FINAL),'-vf','blackdetect=d=0.1:pix_th=0.08:pic_th=0.995','-an','-f','null','-'],capture_output=True,text=True,check=True).stderr
black_events=[line.strip() for line in black.splitlines() if 'black_start:' in line]
assert not black_events,black_events
layout=json.loads((OUT/'layout-validation.json').read_text())
assert layout['issue_count']==0
report={'status':'PASS','file':FINAL.name,'width':1920,'height':1080,'fps':30,'duration_seconds':46,'frames':1380,'video_codec':'h264','audio_codec':'aac','sample_rate':48000,'fully_decoded':True,'video_stream_copied_unchanged':True,'video_packet_hash':final_hash,'black_frame_events':black_events,'layout_issue_count':0,'sha256':sha(FINAL),'file_bytes':FINAL.stat().st_size,'scope':'Opening only; nine cuts. Final cut extended 42–46 seconds for complete naturally paced narration.'}
(OUT/'final-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
