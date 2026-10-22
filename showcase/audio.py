#!/usr/bin/env python3
"""Mix verified continuous Kyung sections and the user-provided BGM."""
from pathlib import Path
import argparse,array,hashlib,json,subprocess,wave
HERE=Path(__file__).resolve().parent;OUT=HERE.parent/'out/showcase'
def run(args):return subprocess.run(args,check=True,capture_output=True,text=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def wav(p):
 with wave.open(str(p),'rb') as w:
  assert (w.getframerate(),w.getnchannels(),w.getsampwidth())==(48000,1,2)
  return w.readframes(w.getnframes())
def savewav(p,pcm):
 with wave.open(str(p),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(pcm)
def loudness(p):
 r=run(['ffmpeg','-hide_banner','-i',str(p),'-af','loudnorm=I=-17:TP=-1.8:LRA=7:print_format=json','-f','null','-'])
 return json.JSONDecoder().raw_decode(r.stderr[r.stderr.rfind('{'):])[0]
def main():
 OUT.mkdir(parents=True,exist_ok=True);processed=OUT/'processed-voice';processed.mkdir(exist_ok=True)
 m=read(HERE/'narration/manifest.json');tl=read(HERE/'timeline.json');conf=read(HERE/'narration/ko.json')
 duration=tl['duration'];assert duration<=300
 master=wav(HERE/'narration/take.wav');total=round(duration*48000);speech=array.array('h',[0])*total;records=[]
 for i,c in enumerate(m['clips'],1):
  f=HERE/'narration'/Path(c['file']).name;pcm=wav(f);a,b=c['source_start_sample'],c['source_end_sample'];assert pcm==master[a*2:b*2];assert sha(f)==c['sha256']
  rate=c['tempo_ratio'];assert 1<=rate<=1.25
  target=processed/f'vo{i}.wav';run(['ffmpeg','-y','-v','error','-i',str(f),'-af',f'atempo={rate:.12f}','-ar','48000','-ac','1','-c:a','pcm_s16le',str(target)])
  values=array.array('h',wav(target));insertions=[]
  for ins in c.get('timeline_silence_insertions',[]):
   source_seconds=ins.get('at_source_local_seconds',ins.get('source_local_seconds',ins.get('source_local_time',ins.get('source_offset_seconds'))))
   if source_seconds is None:source_seconds=ins['source_seconds']
   seconds=ins.get('duration_seconds',ins.get('seconds',1.0));point=round(source_seconds/rate*48000);count=round(seconds*48000)
   values[point:point]=array.array('h',[0])*count;insertions.append({'processed_sample':point,'samples':count,'source_local_seconds':source_seconds})
  # The aligner quantizes the destination section length to whole video frames.
  start=round(c['timeline_start_seconds']*48000);end=round(c['timeline_end_seconds']*48000);expected=end-start
  delta=expected-len(values)
  assert abs(delta)<48000*.15,('Unexpected atempo length drift',i,delta)
  if delta>0:values.extend(array.array('h',[0])*delta)
  else:values=values[:expected]
  assert end<=total;speech[start:end]=values;records.append({'section_id':c['section_id'],'exact_source_pcm':True,'tempo_ratio':rate,'start_seconds':start/48000,'end_seconds':end/48000,'atempo_length_adjustment_samples':delta,'silence_insertions':insertions})
 raw=OUT/'narration-raw.wav';savewav(raw,speech.tobytes());measured=loudness(raw)
 norm=(f"loudnorm=I=-17:TP=-1.8:LRA=7:measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}:offset={measured['target_offset']}:linear=true")
 voice=OUT/'narration.wav';run(['ffmpeg','-y','-v','error','-i',str(raw),'-af','highpass=f=65,'+norm,'-ar','48000','-ac','1','-c:a','pcm_s16le',str(voice)])
 bgm=HERE/conf['bgm'];music=OUT/'bgm-loop.wav'
 # Three source repetitions with overlapping crossfades cover up to five minutes.
 graph=f'[0:a]aresample=48000,asplit=3[a][b][c];[a][b]acrossfade=d=3:c1=tri:c2=tri[ab];[ab][c]acrossfade=d=3:c1=tri:c2=tri,atrim=duration={duration}[music]'
 run(['ffmpeg','-y','-v','error','-i',str(bgm),'-filter_complex',graph,'-map','[music]','-ar','48000','-ac','2','-c:a','pcm_s16le',str(music)])
 graph=(f'[0:a]asplit=2[side][speech];[1:a]volume=0.20,afade=t=in:st=0:d=1,afade=t=out:st={duration-1.5}:d=1.5[music];[music][side]sidechaincompress=threshold=0.018:ratio=4:attack=18:release=300:makeup=1[ducked];[speech][ducked]amix=inputs=2:normalize=0:dropout_transition=0,alimiter=limit=0.841395:level=false,atrim=duration={duration}[mix]')
 mix=OUT/'audio.wav';run(['ffmpeg','-y','-v','error','-i',str(voice),'-i',str(music),'-filter_complex',graph,'-map','[mix]','-ar','48000','-ac','2','-c:a','pcm_s16le',str(mix)])
 run(['ffmpeg','-v','error','-i',str(mix),'-f','null','-'])
 with wave.open(str(mix),'rb') as w:assert w.getnframes()==total and w.getnchannels()==2
 report={'status':'PASS','duration':duration,'sample_rate':48000,'channels':2,'samples':total,'audio_sha256':sha(mix),'master_sha256':sha(HERE/'narration/take.wav'),'voice':conf['voice_name'],'voice_id':conf['voice_id'],'model_id':conf['model_id'],'single_take':True,'bgm_source_sha256':sha(bgm),'bgm_title':'Comprehension','bgm_artist':'Frank Jonsson','bgm_crossfade_seconds':3,'clips':records,'mix_loudness':loudness(mix),'voice_settings_limit':conf.get('settings_limit'),'notes':['All spoken content remains from the same continuous take. Pitch-preserving tempo adjustment fits the user-mandated five-minute limit.']}
 (OUT/'audio-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':'PASS','duration':duration,'clips':len(records),'loudness':report['mix_loudness']['input_i'],'tempo':records[0]['tempo_ratio']}))
if __name__=='__main__':main()
