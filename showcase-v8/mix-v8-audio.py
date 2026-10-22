#!/usr/bin/env python3
"""New task narration and continuous approved music; exact outer PCM reuse."""
from pathlib import Path
import hashlib,json,math,re,subprocess,wave
import numpy as np
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parent/'out/showcase-v8';SR=48000
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(args):return subprocess.run(args,check=True,capture_output=True,text=True)
def read(p):
 with wave.open(str(p))as w:
  assert w.getframerate()==SR and w.getsampwidth()==2
  return np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,w.getnchannels()).copy()
def write(p,a):
 a=np.clip(np.rint(a),-32768,32767).astype('<i2')
 with wave.open(str(p),'wb')as w:w.setnchannels(a.shape[1]);w.setsampwidth(2);w.setframerate(SR);w.writeframes(a.tobytes())
def stats(a,step=.1):
 n=round(SR*step);a=a[:len(a)//n*n].astype(np.float64)/32768
 return np.sqrt(np.mean(a.reshape(-1,n,a.shape[1])**2,axis=(1,2)))
def db(a):return 20*np.log10(np.maximum(a,1e-12))
def main():
 OUT.mkdir(parents=True,exist_ok=True);audit=OUT/'audio-audit';audit.mkdir(exist_ok=True)
 tl=json.loads((ROOT/'timeline.json').read_text());manifest=json.loads((ROOT/'narration/elevenlabs/manifest.json').read_text())
 assert not tl.get('preview_only') and tl['revision']==8 and tl['tempo']==1
 assert len(manifest['cuts'])==12 and manifest['required_output_tempo']==1
 alignment=ROOT/'narration/elevenlabs/alignment-report.json';aligned=json.loads(alignment.read_text())
 assert sha(alignment)==tl['alignment_report_sha256']
 assert sha(ROOT/'narration/elevenlabs/take.wav')==aligned['master_sha256']==manifest['master']['sha256']
 total=tl['frames']*1600;outer=tl['outer_audio'];start=outer['opening_samples'][1];end=outer['ending_destination_sample'];count=end-start
 raw=np.zeros((total,1),dtype='<i2');placements=[]
 master=read(ROOT/'narration/elevenlabs/take.wav')
 for clip in manifest['cuts']:
  section=next(e for e in tl['entries']if e['section_id']==clip['section_id'] and e['kind']=='cut')
  pcm=read(ROOT/clip['file']);a,b=clip['source_start_sample'],clip['source_end_sample'];assert np.array_equal(pcm,master[a:b])
  dest=section['start_frame']*1600;last=max(e['end_frame']for e in tl['entries']if e['section_id']==clip['section_id'])*1600
  assert dest+len(pcm)<=last and np.count_nonzero(raw[dest:dest+len(pcm)])==0
  raw[dest:dest+len(pcm)]=pcm;placements.append({'section_id':clip['section_id'],'start_sample':dest,'end_sample':dest+len(pcm),'source_start_sample':a,'source_end_sample':b,'exact_master_pcm':True,'file_sha256':sha(ROOT/clip['file'])})
 rawfile=OUT/'narration-raw.wav';write(rawfile,raw)
 loud=run(['ffmpeg','-v','info','-i',str(rawfile),'-af','loudnorm=I=-18.5:TP=-3.5:LRA=9:print_format=json','-f','null','-'])
 measured=json.loads(re.search(r'\{\s*"input_i".*?\}',loud.stderr,re.S).group())
 filt='loudnorm=I=-18.5:TP=-3.5:LRA=9:linear=true:print_format=json:'+':'.join(f'{k}={measured[v]}'for k,v in [('measured_I','input_i'),('measured_TP','input_tp'),('measured_LRA','input_lra'),('measured_thresh','input_thresh'),('offset','target_offset')])
 normalized=OUT/'narration.wav'
 second=run(['ffmpeg','-y','-v','info','-i',str(rawfile),'-af',filt,'-ar',str(SR),'-ac','1','-c:a','pcm_s16le',str(normalized)])
 voice=read(normalized);assert len(voice)==total
 approved_file=ROOT/outer['approved_file'];approved_wav=audit/'approved-v6.wav'
 run(['ffmpeg','-y','-v','error','-i',str(approved_file),'-ar',str(SR),'-ac','2','-c:a','pcm_s16le',str(approved_wav)])
 approved=read(approved_wav);tail_a,tail_b=outer['ending_source_samples'];assert len(approved)>=tail_b
 source=ROOT/'assets/bgm/1-ES_Comprehension-Frank-Jonsson-1-.mp3';source_wav=audit/'bgm-original.wav'
 run(['ffmpeg','-y','-v','error','-i',str(source),'-ar',str(SR),'-ac','2','-c:a','pcm_s16le',str(source_wav)])
 original=read(source_wav);period=round(128*60/113*SR);overlap=round(4*60/113*SR);core=original[39*SR:39*SR+period+overlap].astype(np.float64)
 assert len(core)==period+overlap
 loop=np.zeros((total,2),dtype=np.float64);crossfades=[]
 for p in range(0,count,period):
  n=min(len(core),count-p);dst=start+p
  if p==0:loop[dst:dst+n]=core[:n];continue
  nfade=min(overlap,n);phase=np.linspace(0,math.pi/2,nfade)
  loop[dst:dst+nfade]=loop[dst:dst+nfade]*np.cos(phase)[:,None]+core[:nfade]*np.sin(phase)[:,None]
  if n>nfade:loop[dst+nfade:dst+n]=core[nfade:n]
  crossfades.append({'start':dst/SR,'end':(dst+nfade)/SR})
 loopfile=OUT/'bgm-loop.wav';write(loopfile,loop)
 basefile=audit/'music-base.wav';duckfile=audit/'music-ducked.wav'
 # Complete the compressor's last processing block, then trim to exact samples.
 # This internal zero padding never lengthens the delivered film or the voice.
 graph=f'[0:a]apad=pad_len={SR}[side];[1:a]apad=pad_len={SR},volume=0.125,asplit=2[basepre][music];[basepre]atrim=end_sample={total}[base];[music][side]sidechaincompress=threshold=0.018:ratio=4:attack=45:release=650:makeup=1:mix=0.60,atrim=end_sample={total}[duck]'
 run(['ffmpeg','-y','-v','error','-i',str(normalized),'-i',str(loopfile),'-filter_complex',graph,'-map','[base]','-c:a','pcm_s16le',str(basefile),'-map','[duck]','-c:a','pcm_s16le',str(duckfile)])
 base=read(basefile);music=read(duckfile);assert len(music)==total
 ramp=round(1.2*SR);curve=.5-.5*np.cos(np.linspace(0,math.pi,ramp))
 entry=read(ROOT/'assets/bgm/v6-body-entry-music.wav');exit=read(ROOT/'assets/bgm/v6-body-exit-music.wav');assert len(entry)==len(exit)==ramp
 music[start:start+ramp]=np.rint(entry*(1-curve[:,None])+music[start:start+ramp]*curve[:,None]).astype('<i2')
 music[end-ramp:end]=np.rint(music[end-ramp:end]*(1-curve[:,None])+exit*curve[:,None]).astype('<i2')
 mix=voice.astype(np.int32)+music.astype(np.int32);assert np.max(np.abs(mix[start:end]))<32767,'Mix clips; reduce music gain with explicit evidence before export.'
 mix[:start]=approved[:start];mix[end:]=approved[tail_a:tail_b]
 final=OUT/'audio.wav';write(final,mix);write(audit/'body-music-final.wav',music)
 voice_db=db(stats(np.repeat(voice,2,axis=1)));music_db=db(stats(music));base_rms=stats(base);duck_rms=stats(read(duckfile));ratios=np.divide(duck_rms,base_rms,out=np.ones_like(base_rms),where=base_rms>1e-8);time=np.arange(len(music_db))*.1
 body=(time>=start/SR+1.2)&(time<end/SR-1.2);active=body&(voice_db>-32);gap=voice_db-music_db
 checks={'all_twelve_exact_master_pcm_slices':all(p['exact_master_pcm']for p in placements),'all_source_sections_complete':len(placements)==12,'source_tempo_unchanged':tl['tempo']==1,'opening_pcm_identical':np.array_equal(mix[:start],approved[:start]),'ending_pcm_identical':np.array_equal(mix[end:],approved[tail_a:tail_b]),'exact_frame_locked_sample_count':len(mix)==total,'no_100ms_body_music_zero':not np.any(stats(music)[body]==0),'duck_floor_above_minus_8_1_db':float(np.min(db(ratios)[body]))>=-8.1,'no_mix_clipping':int(np.max(np.abs(mix)))<32767,'speech_six_db_above_music_95_percent':float(np.percentile(gap[active],5))>=6}
 checks={k:bool(v)for k,v in checks.items()}
 report={'status':'PASS'if all(checks.values())else'REVIEW','revision':8,'checks':checks,'duration':total/SR,'sample_rate':SR,'channels':2,'samples':total,'audio_file':'audio.wav','audio_sha256':sha(final),'voice':'Kyung - Warm, Calm and Clear','new_task_narration':True,'tempo':1,'opening_and_ending_reused':True,'approved_source_sha256':sha(approved_file),'new_master_sha256':sha(ROOT/'narration/elevenlabs/take.wav'),'normalization':{'target_integrated_lufs':-18.5,'true_peak_db':-3.5,'first_pass':measured,'second_pass':json.loads(re.search(r'\{\s*"input_i".*?\}',second.stderr,re.S).group())},'bgm':{'source_sha256':sha(source),'source_track':'Comprehension / Frank Jonsson','base_gain':.125,'same_repaired_loop_policy_as_revision6':True,'source_speed_changed':False,'bpm':113,'period_beats':128,'overlap_beats':4,'crossfades':crossfades,'duck_wet_mix':.6,'duck_dry_floor':.4,'body_boundary_music_blend_seconds':1.2,'minimum_duck_db':float(np.min(db(ratios)[body])),'body_music_rms_dbfs_p05_median_p95':list(map(float,np.percentile(music_db[body],[5,50,95]))),'speech_minus_music_db_p05_median_p95':list(map(float,np.percentile(gap[active],[5,50,95])))},'placements':placements,'scope':'PCM identity and objective envelope checks. Subjective voice, pronunciation and BGM listening acceptance are separate.'}
 report['input_bindings']=[{'file':p,'sha256':sha(ROOT/p)}for p in ['timeline.json','narration/tasks-ko.json','narration/elevenlabs/manifest.json','narration/elevenlabs/alignment-report.json','narration/elevenlabs/take.wav','assets/bgm/1-ES_Comprehension-Frank-Jonsson-1-.mp3','narration/revision5-approved-audio.m4a','assets/bgm/v6-body-entry-music.wav','assets/bgm/v6-body-exit-music.wav']]
 (OUT/'audio-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(ROOT/'narration/elevenlabs/mix-provenance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':report['status'],'checks':checks,'duration':total/SR,'music_gap_p05':float(np.percentile(gap[active],5))},ensure_ascii=False))
 assert all(checks.values()),'Audio review required; see audio-validation.json.'
if __name__=='__main__':main()
