#!/usr/bin/env python3
"""Verify Revision11 ZIP and reproduce four constant-gain WAVs locally.

The locked video packet stream is reused; no visual rerender, new69 PNGs,
whole-video playback, external generation or transcription is performed.
"""
from pathlib import Path
import argparse,importlib.util,io,json,math,os,stat,subprocess,sys,tempfile,unicodedata,wave,zipfile
import numpy as np
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parent/'out/showcase-v11'
spec=importlib.util.spec_from_file_location('v11_export',ROOT/'package-source.py');export=importlib.util.module_from_spec(spec);spec.loader.exec_module(export)
sha=export.sha;file_sha=export.file_sha;relative=export.relative;passing=export.passing
WAV_NAMES=export.WAV_NAMES;SAMPLES=15120000;BASE='visual-source-v10/'
BUNDLED=Path('/Users/jk/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3')
def save(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def wav(data):
 with wave.open(io.BytesIO(data),'rb')as w:
  info={'sample_rate':w.getframerate(),'channels':w.getnchannels(),'sample_width':w.getsampwidth(),'samples':w.getnframes()};pcm=w.readframes(w.getnframes())
 assert info['sample_rate']==48000 and info['sample_width']==2
 return info,pcm

def identity(p):
 data=Path(p).read_bytes();info,pcm=wav(data);return {k:info[k]for k in ['samples','sample_rate','channels']}|{'sha256':sha(data),'pcm_sha256':sha(pcm)}
def streamhash(p):return subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-'],text=True).strip()
def verify_raw_gain_music(read,manifest,baseline,tl):
 placement=json.loads(read(BASE+'narration/placement-manifest.json'));parts=placement['source_parts'];source=json.loads(read(BASE+'narration/two-part-sources.json'));config=json.loads(read(BASE+'narration/ko.json'))
 assert len(parts)==2 and [len(p['cut_ids'])for p in parts]==[33,35]and[c for p in parts for c in p['cut_ids']]==[c['id']for b in config['blocks']for c in b['cuts']]
 assert placement['piece_count']==77 and len(placement['pieces'])==77 and len(placement['cuts'])==68 and placement['speech_tempo']==1 and placement['spoken_samples_removed']==0
 assert sha(read(BASE+'narration/placement-manifest.json'))==manifest['placement_manifest_sha256']and manifest['source_identity_sha256']==placement['source_identity_sha256']
 auth=source['authorization']if isinstance(source['authorization'],dict)else{'path':source['authorization'],'sha256':source['authorization_sha256']};assert sha(read(BASE+auth['path']))==auth['sha256']
 payload={'generation_mode':'two_part_with_user_authorization','authorization_sha256':auth['sha256'],'parts':[{k:p[k]for k in ['part_id','master_sha256','asr_sha256','cut_ids','provenance']}for p in parts]}
 assert sha(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())==manifest['source_identity_sha256']
 buffers={};byid={}
 for p in parts:
  data=read(BASE+p['master']);info,pcm=wav(data);assert(info['channels'],info['samples'])==(1,p['samples'])and sha(data)==p['master_sha256']and sha(pcm)==p['master_pcm_sha256']and sha(read(BASE+p['asr']))==p['asr_sha256']
  buffers[p['part_id']]=np.frombuffer(pcm,dtype='<i2');byid[p['part_id']]=p
 raw=np.zeros(SAMPLES,dtype='<i2');last=0;piece_proofs=[]
 for p in placement['pieces']:
  a,b=p['source_local_start_sample'],p['source_local_end_sample'];c,d=p['destination_start_sample'],p['destination_end_sample'];part=byid[p['source_part_id']]
  assert p['source_file']==part['master']and p['source_file_sha256']==part['master_sha256']and 0<=a<b<=part['samples']and last<=c<d<=SAMPLES and d-c==b-a
  chunk=buffers[p['source_part_id']][a:b];assert sha(chunk.tobytes())==p['pcm_sha256'];raw[c:d]=chunk;last=d;piece_proofs.append(p['pcm_sha256'])
 actual={n:identity(OUT/n)for n in WAV_NAMES};raw_data=(OUT/'narration-raw.wav').read_bytes();raw_info,raw_pcm=wav(raw_data)
 assert raw_info['channels']==1 and raw_info['samples']==SAMPLES and raw_pcm==raw.tobytes()and sha(raw_data)==baseline['baseline_raw_sha256']==placement['raw_output']['sha256']and sha(raw_pcm)==placement['raw_output']['pcm_sha256']
 assert not np.any(raw[311*48000:])and manifest['files']==actual
 gain=manifest['gain_factor'];assert math.isclose(gain,10**(manifest['constant_voice_gain_db']/20),rel_tol=1e-14)
 _,voice_pcm=wav((OUT/'narration.wav').read_bytes());voice=np.frombuffer(voice_pcm,dtype='<i2');expected=np.rint(raw.astype(np.float64)*gain).astype(np.int64)
 assert np.max(np.abs(expected))<32767 and np.array_equal(voice.astype(np.int64),expected)and not np.any(voice[311*48000:])
 music_data=read(BASE+'assets/bgm/revision9-approved-music.wav');music_info,original_music=wav(music_data);assert music_info=={'sample_rate':48000,'channels':2,'sample_width':2,'samples':15096000}
 _,music_pcm=wav((OUT/'bgm-loop.wav').read_bytes());assert music_pcm==original_music+bytes(24000*4)and actual['bgm-loop.wav']['sha256']==baseline['baseline_music_sha256']
 music=np.frombuffer(music_pcm,dtype='<i2').reshape(-1,2);_,mix_pcm=wav((OUT/'audio.wav').read_bytes());mix=np.frombuffer(mix_pcm,dtype='<i2').reshape(-1,2);combined=voice.astype(np.int64)[:,None]+music.astype(np.int64)
 assert np.max(np.abs(combined))<32767 and np.array_equal(mix.astype(np.int64),combined)
 assert sha(read('timeline.json'))==sha(read(BASE+'timeline.json'))==baseline['timeline_sha256']==manifest['timeline_sha256']and tl['entries'][-1]['start_frame']==9330
 return {'retained_source_pieces':77,'source_utterances':68,'raw_file_sha256':actual['narration-raw.wav']['sha256'],'raw_PCM_sha256':actual['narration-raw.wav']['pcm_sha256'],'gain_factor':gain,'constant_gain_db':manifest['constant_voice_gain_db'],'voice_sample_error_count':0,'music_PCM_preserved':True,'integer_mix_sample_error_count':0,'new_pitch_or_time_DSP':False,'last4s_voice_literal_zero':True,'piece_PCM_sha256':piece_proofs}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('archive',nargs='?',type=Path,default=OUT/export.ARCHIVE_NAME);ap.add_argument('--package-only',action='store_true');args=ap.parse_args();archive=args.archive.resolve()
 if not archive.is_file():print(json.dumps({'status':'WAITING_FOR_FINAL_ARCHIVE','verification_performed':False,'reproduction_performed':False}));return 2
 package={'revision':11,'status':'IN_PROGRESS','checks':{},'tested_archive':{'file':str(archive),'bytes':archive.stat().st_size,'sha256':file_sha(archive)},'scope':'Final ZIP privacy/inventory, preserved172-file snapshot, fixed video, original77-piece PCM and constant-gain-only audio. No new rendering or human listening.'};repro={'revision':11,'status':'NOT_RUN','checks':{},'new_speech_generation':False,'new_visual_render':False,'new_native_PNG_generation':False,'whole_video_encode_or_playback_repeated':False};active=package
 def check(r,name,ok,details):
  r['checks'][name]={'pass':bool(ok),'details':details}
  if not ok:raise AssertionError(name)
 try:
  with zipfile.ZipFile(archive)as z:
   infos=z.infolist();names=[x.filename for x in infos if not x.is_dir()];bad=[];seen={};collision=[]
   for i in infos:
    key=unicodedata.normalize('NFC',i.filename.rstrip('/')).casefold()
    if not relative(i.filename)or stat.S_ISLNK(i.external_attr>>16):bad.append(i.filename)
    if key in seen and seen[key]!=i.filename:collision.append([seen[key],i.filename])
    seen[key]=i.filename
   check(package,'safe_relative_paths_no_symlinks_or_collisions',not bad and not collision,{'invalid':bad,'collisions':collision})
   check(package,'unique_archive_members',len(names)==len(set(names)),{'files':len(names)})
   data=z.read('SOURCE_MANIFEST.json');manifest=json.loads(data);rows=manifest['files'];listed=[r['file']for r in rows]
   check(package,'exact_manifest_inventory',len(listed)==len(set(listed))and set(names)==set(listed)|{'SOURCE_MANIFEST.json'},{'manifest_rows':len(rows)})
   mismatch=[];secrets=[];workspace_bad=[];before={};redactions={r['file']:r for r in manifest.get('export_redactions',[])};redacted=[]
   for row in rows:
    payload=z.read(row['file'])
    if sha(payload)!=row['sha256']or len(payload)!=row['bytes']:mismatch.append(row['file'])
    secrets.extend(export.signed_hits(row['file'],payload))
    if row['file'].startswith(export.SOURCE_PREFIX):
     rel=row['file'][len(export.SOURCE_PREFIX):];path=ROOT/rel
     if not path.is_file():workspace_bad.append(rel);continue
     original=path.read_bytes();before[rel]=sha(original)
     if before[rel]!=row['sha256']:
      item=redactions.get(row['file']);clean,fields=export.sanitized_export(row['file'],original)
      if item and item['original_sha256']==before[rel]and item['packaged_sha256']==sha(clean)==row['sha256']and fields==item['removed_fields']:redacted.append(rel)
      else:workspace_bad.append(rel)
   check(package,'all_member_SHA256_and_sizes_match',not mismatch,{'files':len(rows),'mismatch':mismatch})
   check(package,'whole_ZIP_CRC_verified',True,{'method':'Every member completely read with ZipExtFile CRC validation.','members':len(rows)+1})
   secrets.extend(export.signed_hits('SOURCE_MANIFEST.json',data));check(package,'signed_generation_URL_residue_zero',not secrets,{'count':len(secrets),'key_paths_only':secrets,'URL_values_printed':False})
   check(package,'current_workspace_sources_exact_with_declared_URL_redactions',not workspace_bad,{'source_files':len(before),'redacted_files':redacted,'mismatch':workspace_bad})
   def read(name):
    assert relative(name)and export.SOURCE_PREFIX+name in names,'Missing/nonrelative source: '+str(name)
    return z.read(export.SOURCE_PREFIX+name)
   def src(name):return json.loads(read(name))
   def receipt(name):return json.loads(z.read('out/showcase-v11/'+name))
   authorization=src('authorization.json');baseline=src('baseline-provenance.json');processing=src('audio-processing-manifest.json');tl=src('timeline.json');locked=manifest['locked_video']
   flags=['no_pitch_processor','no_time_processor','no_filter_or_EQ_or_compressor','no_new_speech_generation']
   check(package,'direct_natural_pitch_only_authorization',manifest['revision']==11 and manifest['production_complete']is True and manifest['delivery_status']=='FINAL'and manifest['pitch_cents']==processing['pitch_cents']==0 and manifest['speech_tempo']==processing['speech_tempo']==1 and manifest['new_speech_generation']is False and manifest['voice_processing']=='single_constant_gain_only'and authorization['authorization_source']=='direct_user_request_in_current_chat'and authorization['pitch_shift_cents']==0 and authorization['pitch_or_time_processor_allowed']is False and authorization['speech_tempo']==1 and authorization['new_remote_generation_authorized']is False and all(processing[k]is True for k in flags),{'pitch_cents':0,'tempo':1,'new_generation':False,'waveform_change':'one constant scalar gain'})
   snapshot=export.snapshot_check(read,baseline,redactions);snapshot_names={n[len(export.SOURCE_PREFIX+BASE):]for n in names if n.startswith(export.SOURCE_PREFIX+BASE)}
   shape=(tl['frames'],tl['duration'],len(tl['entries']))==(9450,315,69)and len([e for e in tl['entries']if e['kind']=='cut'])==68 and tl['entries'][-1]['start_frame']==9330
   check(package,'snapshot172_and_timeline_preserved',snapshot_names=={r['file']for r in baseline['source_files']}and shape and sha(read('timeline.json'))==sha(read(BASE+'timeline.json'))==baseline['timeline_sha256']and manifest['snapshot']['prior_audio_and_visual_builders_are_historical']is True and sha(read('baseline-provenance.json'))==manifest['snapshot']['baseline_provenance_sha256'],{'snapshot':snapshot,'timeline_sha256':baseline['timeline_sha256'],'duration':315,'frames':9450,'entries':69})
   required=['README.md','package-source.py','verify-source-package.py','audio.py','finish.py','validate-final.py','review-audio.py','review-encoded-audio.py','authorization.json','baseline-provenance.json','timeline.json','audio-processing-manifest.json','assets/video/locked-silent.mp4','baseline-reviews/encoded-visual-review.json','baseline-reviews/playback-validation.json']
   missing=[p for p in required if export.SOURCE_PREFIX+p not in names];check(package,'standalone_active_runtime_and_locked_video_present',not missing,{'required':len(required),'missing':missing,'historical_canvas_or_Swift_not_executed':True})
   reports={n:receipt(n)for n in export.REQUIRED_RECEIPTS};final=reports['final-validation.json'];mux=reports['mux-validation.json'];audio=reports['audio-validation.json'];state=reports['SOURCE_STATUS.json'];current=OUT/export.VIDEO_NAME;video_sha=file_sha(current)if current.is_file()else None;stale=[];visited=set()
   def linked(value,owner):
    for row in value.get('receipts',[]):
     assert relative(row['file']);name='out/showcase-v11/'+row['file'];actual=sha(z.read(name));red=redactions.get(name)
     if actual!=row['sha256']and not(red and red['original_sha256']==row['sha256']and red['packaged_sha256']==actual):stale.append({'owner':owner,'file':name})
     if name not in visited:visited.add(name);linked(json.loads(z.read(name)),name)
   for n,r in reports.items():linked(r,n)
   check(package,'current_final_media_and_scoped_receipts_bound',all(passing(r)for n,r in reports.items()if n!='SOURCE_STATUS.json')and final.get('production_complete')is True and state.get('production_complete')is True and state.get('revision')==11 and video_sha==manifest['final_video_sha256']==export.video_hash(final)==export.video_hash(mux)and video_sha is not None and not stale,{'video_sha256':video_sha,'stale_receipts':stale,'fresh_playback_not_claimed':True})
   bound=export.bindings(processing);invalid=[p for p,h in bound.items()if not relative(p)or export.SOURCE_PREFIX+p not in names or sha(read(p))!=h]
   check(package,'active_audio_input_paths_hashes_and_four_outputs_bound',bool(bound)and not invalid and processing['files']==audio['files']and manifest['active_audio']['processing_manifest']=='audio-processing-manifest.json'and sha(read('audio-processing-manifest.json'))==manifest['active_audio']['processing_manifest_sha256']and processing['source_identity_sha256']==audio['source_identity_sha256']==manifest['active_audio']['source_identity_sha256']and processing['files']=={n:identity(OUT/n)for n in WAV_NAMES}, {'bindings':len(bound),'invalid':invalid,'WAVs':4})
   proof=verify_raw_gain_music(read,processing,baseline,tl);check(package,'original77_PCM_pieces_single_gain_same_BGM_integer_mix',proof['voice_sample_error_count']==proof['integer_mix_sample_error_count']==0,proof)
   locked_sha=sha(read(locked['file']));reference=src('baseline-reviews/encoded-visual-review.json');playback=src('baseline-reviews/playback-validation.json');visual=reports['visual-preservation-validation.json']
   check(package,'locked_video_SHA_packets_and_prior_playback_scope',locked_sha==locked['sha256']==baseline['locked_silent_sha256']and mux['video_stream_sha256']==locked['video_stream_sha256']==reference['video_stream_sha256']==visual['video_stream_sha256']and playback['status']=='PASS'and visual['new_full_browser_playback_performed']is False,{'locked_sha256':locked_sha,'video_stream_sha256':locked['video_stream_sha256'],'baseline_playback_sha256':sha(read('baseline-reviews/playback-validation.json')),'new_full_playback':False})
   assert len(package['checks'])==14;ident=export.source_identity(rows);assert ident==manifest['immutable_source_identity'];package.update(status='PASS',immutable_source_identity=ident,source_manifest_sha256=sha(data),archive_file_count=len(names))
   prior=OUT/'source-reproduction-validation.json'
   if args.package_only and prior.is_file():
    old=json.loads(prior.read_text())
    if old.get('status')=='SOURCE_PASS':assert old['immutable_source_identity']==ident;package['same_immutable_source_as_fresh_reproduction']=True
   save(OUT/'source-package-validation.json',package)
   if args.package_only:print(json.dumps({'status':'PASS','checks':14,'archive_sha256':package['tested_archive']['sha256'],'immutable_source_identity':ident}));return 0
   temp=Path(tempfile.mkdtemp(prefix='media-maker-v11-source-smoke-',dir='/private/tmp'));z.extractall(temp)
  active=repro;extracted=temp/'showcase-v11';tempout=temp/'out/showcase-v11';source_rows=[r for r in rows if r['file'].startswith(export.SOURCE_PREFIX)];expected={n:identity(OUT/n)for n in WAV_NAMES}
  repro.update(tested_archive=package['tested_archive'],immutable_source_identity=ident,source_manifest_sha256=package['source_manifest_sha256'],extraction_directory=str(temp),source_identity_sha256=processing['source_identity_sha256'])
  check(repro,'fresh_extraction_without_prior_project_folders',not any((temp/f'showcase-v{i}').exists()for i in range(1,11)),{'directory':str(temp),'historical_snapshot_is_inside_v11':True})
  check(repro,'all_extracted_source_hashes_exact',all(file_sha(temp/r['file'])==r['sha256']for r in source_rows),{'files':len(source_rows)})
  actual_stream=streamhash(extracted/locked['file']);check(repro,'locked_video_file_and_packet_hashes_exact',file_sha(extracted/locked['file'])==locked['sha256']and actual_stream==locked['video_stream_sha256'],{'file_sha256':locked['sha256'],'video_stream_sha256':actual_stream,'whole_decode_or_render_repeated':False})
  python=os.environ.get('AUDIO_PYTHON',str(BUNDLED)if BUNDLED.is_file()else sys.executable);log=OUT/'source-reproduction-audio.log'
  with log.open('w')as f:run=subprocess.run([python,'audio.py'],cwd=extracted,stdout=f,stderr=subprocess.STDOUT)
  check(repro,'active_natural_voice_audio_entrypoint_succeeded',run.returncode==0,{'return_code':run.returncode,'command':'python3 audio.py','python':python,'log':str(log),'no_CoreAudio_Swift_or_canvas':True})
  actual={n:identity(tempout/n)for n in WAV_NAMES};check(repro,'all_four_WAV_file_and_PCM_hashes_exact',actual==expected,{'expected':expected,'actual':actual})
  rebuilt=json.loads((tempout/'audio-validation.json').read_text());check(repro,'rebuilt_natural_pitch_identity_and_relative_bindings_pass',passing(rebuilt)and rebuilt['pitch_cents']==0 and rebuilt['speech_tempo']==1 and rebuilt['source_identity_sha256']==processing['source_identity_sha256']and all(relative(p)and file_sha(extracted/p)==h for p,h in export.bindings(rebuilt).items()),{'status':rebuilt['status'],'input_bindings':len(export.bindings(rebuilt))})
  changed=[r['file']for r in source_rows if file_sha(temp/r['file'])!=r['sha256']];check(repro,'archived_sources_unchanged_after_execution',not changed,{'source_files':len(source_rows),'changed':changed})
  changed=[p for p,h in before.items()if file_sha(ROOT/p)!=h];check(repro,'original_sources_and_four_WAV_outputs_unchanged',not changed and expected=={n:identity(OUT/n)for n in WAV_NAMES},{'source_files':len(before),'changed':changed})
  repro.update(status='SOURCE_PASS',audio_outputs=actual,locked_video_sha256=locked['sha256'],locked_video_stream_sha256=actual_stream,limitations=['FourWAV byte/PCM reproduction and locked-video packet identity only. No69 PNG rerender, new whole-video playback, external speech generation or subjective listening.','Historical172-file snapshot remains separate from the active natural-pitch audio runtime.']);save(OUT/'source-reproduction-validation.json',repro)
  print(json.dumps({'package_status':'PASS','package_checks':14,'reproduction_status':'SOURCE_PASS','reproduction_checks':len(repro['checks']),'WAV_file_matches':4,'PCM_matches':4,'archive_sha256':package['tested_archive']['sha256'],'immutable_source_identity':ident}));return 0
 except Exception as e:
  active.update(status='FAIL',error={'type':type(e).__name__,'check':str(e)});save(OUT/'source-package-validation.json',package)
  if active is repro:save(OUT/'source-reproduction-validation.json',repro)
  print(json.dumps({'status':'FAIL','type':type(e).__name__,'check':str(e)}));return 1
if __name__=='__main__':raise SystemExit(main())
