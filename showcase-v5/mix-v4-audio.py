#!/usr/bin/env python3
"""Place the slower complete narration and preserve the existing BGM loop clock, gain and fades."""
from pathlib import Path
import array,hashlib,json,subprocess,wave
HERE=Path(__file__).resolve().parent;OUT=HERE.parent/'out/showcase-v5';SR=48000
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(a):return subprocess.run(a,check=True,capture_output=True,text=True)
def pcm(p):
 with wave.open(str(p)) as w:
  assert (w.getframerate(),w.getnchannels(),w.getsampwidth())==(SR,1,2)
  return w.readframes(w.getnframes())
def save(p,data):
 with wave.open(str(p),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes(data)
def loudness(p):
 r=run(['ffmpeg','-hide_banner','-i',str(p),'-af','loudnorm=I=-17:TP=-1.8:LRA=7:print_format=json','-f','null','-'])
 return json.JSONDecoder().raw_decode(r.stderr[r.stderr.rfind('{'):])[0]
def main():
 OUT.mkdir(parents=True,exist_ok=True);m=read(HERE/'narration/revision-manifest-v4.json');tl=read(HERE/'timeline.json');conf=read(HERE/'narration/ko.json')
 source=Path(m['processed_master']['path'])
 if not source.is_absolute():source=HERE/source
 assert sha(source)==m['processed_master']['sha256']
 master=pcm(source);total=tl['frames']*(SR//tl['fps']);voice=bytearray(total*2);recovered=bytearray();records=[];previous=0
 for p in m['placements']:
  a,b=p['source_start_sample'],p['source_end_sample'];dest=p['timeline_start_sample'];count=b-a
  assert a==previous and count==p['sample_count'] and dest+count<=total
  part=master[a*2:b*2];voice[dest*2:(dest+count)*2]=part;recovered.extend(part);previous=b
  records.append({**p,'pcm_sha256':hashlib.sha256(part).hexdigest(),'exact_processed_master_pcm':True})
 assert bytes(recovered)==master,'Source speech samples were omitted, duplicated, or reordered'
 assert abs(m['tempo_ratio']-read(HERE/'narration/processed-continuous-v4-provenance.json')['tempo_ratio'])<1e-12
 speech=OUT/'narration-raw.wav';save(speech,bytes(voice))
 actual=pcm(speech)
 for p in m['placements']:
  a,b=p['source_start_sample'],p['source_end_sample'];dest=p['timeline_start_sample']
  assert actual[dest*2:(dest+b-a)*2]==master[a*2:b*2]
 quiet_regions=[]
 for e in tl['entries']:
  must_quiet=e['kind'] in ['summary','title','silent']
  if must_quiet:
   a=e['start_frame']*(SR//tl['fps']);b=e['end_frame']*(SR//tl['fps']);part=actual[a*2:b*2]
   assert not any(part),(e['section_id'],e['kind'],'narration leaked into silent visual entry')
   quiet_regions.append({'section_id':e['section_id'],'kind':e['kind'],'start':e['start'],'end':e['end'],'narration_pcm_exact_zero':True})
 measured=loudness(speech)
 norm=(f"loudnorm=I=-17:TP=-1.8:LRA=7:measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}:offset={measured['target_offset']}:linear=true")
 normalized=OUT/'narration.wav';run(['ffmpeg','-y','-v','error','-i',str(speech),'-af','highpass=f=65,'+norm,'-ar','48000','-ac','1','-c:a','pcm_s16le',str(normalized)])
 duration=tl['duration'];bgm=HERE/conf['bgm'];music=OUT/'bgm-loop.wav'
 graph=f'[0:a]aresample=48000,asplit=3[a][b][c];[a][b]acrossfade=d=3:c1=tri:c2=tri[ab];[ab][c]acrossfade=d=3:c1=tri:c2=tri,atrim=duration={duration}[music]'
 run(['ffmpeg','-y','-v','error','-i',str(bgm),'-filter_complex',graph,'-map','[music]','-ar','48000','-ac','2','-c:a','pcm_s16le',str(music)])
 graph=(f'[0:a]apad=pad_dur=1,asplit=2[side][speech];[1:a]apad=pad_dur=1,volume=0.20,afade=t=in:st=0:d=1,afade=t=out:st={duration-1.5}:d=1.5[music];[music][side]sidechaincompress=threshold=0.018:ratio=4:attack=18:release=300:makeup=1[ducked];[speech][ducked]amix=inputs=2:normalize=0:dropout_transition=0,alimiter=limit=0.841395:level=false,atrim=duration={duration}[mix]')
 mix=OUT/'audio.wav';run(['ffmpeg','-y','-v','error','-i',str(normalized),'-i',str(music),'-filter_complex',graph,'-map','[mix]','-ar','48000','-ac','2','-c:a','pcm_s16le',str(mix)])
 run(['ffmpeg','-v','error','-i',str(mix),'-f','null','-'])
 with wave.open(str(mix)) as w:assert w.getnframes()==total and w.getnchannels()==2
 oldloop=HERE.parent/'out/showcase-v2/bgm-loop.wav'
 bgm_loop_same=sha(music)==sha(oldloop) if oldloop.exists() else None
 if oldloop.exists():assert bgm_loop_same,'BGM loop clock/PCM changed'
 report={'revision':4,'status':'PASS','duration':duration,'sample_rate':SR,'channels':2,'samples':total,'audio_sha256':sha(mix),'original_master_sha256':sha(HERE/'narration/take.wav'),'processed_master_sha256':sha(source),'voice':conf['voice_name'],'voice_id':conf['voice_id'],'model_id':conf['model_id'],'single_take':True,'tempo_ratio':m['tempo_ratio'],'additional_speed_changes':0,'approved_narration_speed_change':True,'previous_tempo_ratio':m['previous_tempo_ratio'],'voice_extension_seconds':24,'original_source_processed_once':True,'bgm_loop_unchanged_vs_v2':bgm_loop_same,'bgm_loop_sha256':sha(music),'bgm_gain':0.20,'bgm_fade_in_seconds':1,'bgm_fade_out_seconds':1.5,'bgm_source_sha256':sha(bgm),'bgm_title':'Comprehension','bgm_artist':'Frank Jonsson','bgm_crossfade_seconds':3,'pcm_placements':records,'all_processed_source_samples_preserved_once_in_order':True,'all_placements_match_processed_master_pcm':True,'silent_entries':quiet_regions,'per_cut_timing':m['per_cut_timing'],'sections':m['sections'],'mix_loudness':loudness(mix),'notes':['The approved complete original take is processed once at the approved slower factor, using exactly the 24 seconds released by removing four summaries.','Only silence is inserted for visual exposure and chapter separation. No spoken samples are removed or regenerated.']}
 (OUT/'audio-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':'PASS','duration':duration,'pcm_placements':len(records),'silent_entries':len(quiet_regions),'tempo':m['tempo_ratio'],'loudness':report['mix_loudness']['input_i']}))
if __name__=='__main__':main()
