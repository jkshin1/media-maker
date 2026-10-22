#!/usr/bin/env python3
"""Validate final streams, source PCM, timeline, and encoded-video identity."""
from pathlib import Path
import hashlib,json,subprocess,wave
HERE=Path(__file__).resolve().parent;OUT=HERE.parent/'out/showcase'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(a):return subprocess.run(a,capture_output=True,text=True,check=True)
def video_hash(p):return run(['ffmpeg','-v','error','-i',str(p),'-map','0:v:0','-c:v','copy','-f','hash','-hash','sha256','-']).stdout.strip()
def main():
 final=OUT/'RD_Process_AI_Fast_Track_Showcase.mp4';tl=read(HERE/'timeline.json');meta=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(final)]).stdout)
 v=next(s for s in meta['streams'] if s['codec_type']=='video');a=next(s for s in meta['streams'] if s['codec_type']=='audio');checks={}
 checks['duration_under_five_minutes']=float(meta['format']['duration'])<=300
 checks['video_frame_count']=int(v['nb_frames'])==round(tl['duration']*30)
 checks['video_dimensions']=(v['width'],v['height'])==(1920,1080)
 checks['frame_rate']=v['r_frame_rate']=='30/1'
 checks['audio_format']=a['codec_name']=='aac' and int(a['sample_rate'])==48000 and a['channels']==2
 checks['timeline_duration_matches']=abs(float(meta['format']['duration'])-tl['duration'])<.06
 run(['ffmpeg','-v','error','-i',str(final),'-f','null','-']);checks['complete_video_audio_decode']=True
 vh=video_hash(OUT/'video_silent.mp4');fh=video_hash(final);checks['video_stream_copied_exactly']=vh==fh
 m=read(HERE/'narration/manifest.json')
 with wave.open(str(HERE/'narration/take.wav'),'rb') as w:pcm=w.readframes(w.getnframes())
 for c in m['clips']:
  with wave.open(str(HERE/'narration'/Path(c['file']).name),'rb') as w:part=w.readframes(w.getnframes())
  assert part==pcm[c['source_start_sample']*2:c['source_end_sample']*2]
 checks['all_fourteen_original_cuts_match_master_pcm']=True
 render=read(OUT/'render-validation.json')
 checks['render_inputs_unchanged']=all(sha(HERE/i['file'])==i['sha256'] for i in render['inputs'])
 assert all(checks.values()),checks
 report={'status':'PASS_WITH_ASR_VARIANTS','technical_checks':checks,'duration_seconds':float(meta['format']['duration']),'video_duration_seconds':float(v['duration']),'width':v['width'],'height':v['height'],'fps':30,'frames':int(v['nb_frames']),'audio_sample_rate':48000,'channels':2,'file_sha256':sha(final),'video_packet_hash':fh,'voice':'Kyung - Warm, Calm and Clear','bgm':'Comprehension — Frank Jonsson','audio':read(OUT/'audio-validation.json'),'limitations':['Local ASR covered every script block but retains four pronunciation/spelling ambiguities; review-summary.json lists them.','Connected account cannot generate human-action video clips. Photographic plates and procedural camera/UI/data animations were used.','Saved stability/similarity settings are recorded as requested defaults; the Creative Studio schema does not expose independent confirmation.']}
 (OUT/'final-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(OUT/'SHA256SUMS.txt').write_text(f"{report['file_sha256']}  {final.name}\n")
 print(json.dumps({'status':report['status'],'duration':report['duration_seconds'],'frames':report['frames'],'sha256':report['file_sha256']}))
if __name__=='__main__':main()
