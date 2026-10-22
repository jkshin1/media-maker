#!/usr/bin/env python3
"""Verify the authorized Revision10 ZIP and reproduce69 PNGs/four final WAVs.

--package-only verifies a receipt-only repack against the same source identity.
No paid generation, external transcription, MP4 encode, mux or playback occurs.
macOS offline AVAudioUnit reproduction needs a local CoreAudio-capable executor.
"""
from pathlib import Path
import argparse,array,importlib.util,io,json,math,os,stat,subprocess,sys,tempfile,unicodedata,wave,zipfile
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parent/'out/showcase-v10'
spec=importlib.util.spec_from_file_location('revision10_source_export',ROOT/'package-source.py');export=importlib.util.module_from_spec(spec);spec.loader.exec_module(export)
file_sha=export.file_sha;sha=export.sha;relative=export.relative;passing=export.passing
ORDER=['opening','task11','task13','task7','task17','task5','task9','task4','task12','task3','task8','task14','task16','ending']
COUNTS={'task11':5,'task13':5,'task7':5,'task17':4,'task5':5,'task9':5,'task4':5,'task12':3,'task3':4,'task8':4,'task14':5,'task16':5}
WAV_NAMES=['audio.wav','narration.wav','narration-raw.wav','bgm-loop.wav'];SAMPLES=15120000
BUNDLED=Path('/Users/jk/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3')
GEOMETRY=['section_id','kind','cut_id','cut_index','start_frame','end_frame','start','end','caption']
def save(path,obj):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def wav(data):
 with wave.open(io.BytesIO(data),'rb')as w:
  info={'sample_rate':w.getframerate(),'channels':w.getnchannels(),'sample_width':w.getsampwidth(),'sample_count':w.getnframes()};pcm=w.readframes(w.getnframes())
 return info,pcm
def wav_identity(path):
 data=Path(path).read_bytes();info,pcm=wav(data);return {**info,'sha256':sha(data),'pcm_sha256':sha(pcm)}
def geometry(entries):return [{k:e[k]for k in GEOMETRY}for e in entries]
def words(value):return [w for s in value['segments']for w in s.get('words',[])]
def check_pcm(read,source,placement,config,tl,processing):
 """Rebuild pre-DSP placement independently from actual two-source PCM bytes."""
 parts=placement['source_parts'];assert len(parts)==len(source['parts'])==2
 ids=[c['id']for b in config['blocks']for c in b['cuts']]
 assert [len(p['cut_ids'])for p in parts]==[33,35]and[c for p in parts for c in p['cut_ids']]==ids
 auth={'path':source['authorization'],'sha256':source['authorization_sha256']}if isinstance(source['authorization'],str)else source['authorization']
 a=json.loads(read(auth['path']));assert sha(read(auth['path']))==auth['sha256']and a['authorization_source']=='direct_user_reply_in_current_chat'and a['generation_mode']=='two_part_with_user_authorization'and a['speech_speed_ratio']==1
 buffers={};asrs={};part_byid={};source_rows=[];offset=0
 for descriptor,p in zip(source['parts'],parts):
  assert all(descriptor[k]==p[k]for k in ['part_id','master','asr','cut_ids'])
  provenance=descriptor['provenance']
  if isinstance(provenance,str):provenance=[{'path':provenance,'sha256':descriptor['provenance_sha256']}]
  assert provenance==p['provenance']
  data=read(p['master']);info,pcm=wav(data);assert info=={'sample_rate':48000,'channels':1,'sample_width':2,'sample_count':p['samples']}
  assert sha(data)==p['master_sha256']and sha(pcm)==p['master_pcm_sha256']and sha(read(p['asr']))==p['asr_sha256']
  assert p['virtual_start_sample']==offset and p['virtual_end_sample']==offset+p['samples'];offset+=p['samples']
  buffers[p['part_id']]=pcm;asrs[p['part_id']]=words(json.loads(read(p['asr'])));part_byid[p['part_id']]=p
  imported=False
  for binding in p['provenance']:
   data=read(binding['path']);assert sha(data)==binding['sha256'];v=json.loads(data)
   if 'master_sha256'in v:
    imported=True;assert v['master_file']==p['master']and v['master_sha256']==p['master_sha256']and v['authorization_sha256']==auth['sha256']and v['speech_tempo']==1 and v['generation_mode']=='two_part_with_user_authorization'
    assert(v['voice_id'],v['model_id'],v['language_code'])==(source['voice_id'],source['model_id'],source['language_code'])and sha(read(v['prompt_file']))==v['prompt_sha256']
  assert imported
  source_rows.append({'part_id':p['part_id'],'master_sha256':p['master_sha256'],'pcm_sha256':sha(pcm),'samples':p['samples'],'asr_sha256':p['asr_sha256']})
 identity={'generation_mode':'two_part_with_user_authorization','authorization_sha256':auth['sha256'],'parts':[{k:p[k]for k in ['part_id','master_sha256','asr_sha256','cut_ids','provenance']}for p in parts]}
 source_id=sha(json.dumps(identity,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode());assert source_id==placement['source_identity_sha256']==processing['source_identity_sha256']
 retime=json.loads(read(placement['retime_authorization']));plan_data=read(placement['approved_plan']);plan=json.loads(plan_data)
 assert sha(plan_data)==placement['approved_plan_sha256']==retime['approved_proposal_sha256']and retime['approved_proposal']==placement['approved_plan']
 assert sha(read(placement['retime_authorization']))==placement['retime_authorization_sha256']and retime['authorization_source']=='direct_user_reply_in_current_chat'and(retime['speech_tempo'],retime['pitch_cents'])==(1,315)
 assert geometry(tl['entries'])==geometry(plan['entries'])and placement['cuts']==plan['placements']and placement['audio_groups']==plan['audio_groups']
 for key in ['independent_retime_review','completeness_review']:
  assert sha(read(placement[key]))==placement[key+'_sha256']
 independent=json.loads(read(placement['independent_retime_review']));assert independent['status']=='PROPOSAL_INTERNALLY_FEASIBLE'and all(x['pass']for x in independent['checks'].values())
 completeness=json.loads(read(placement['completeness_review']));assert completeness['source_identity_sha256']==source_id and completeness['status']=='PASS_COMPLETENESS_WITH_ASR_VARIANTS'and all(x['pass']for x in completeness['checks'].values())
 pieces=placement['pieces'];expected=[p for c in plan['placements']for p in c['pieces']]+plan['audio_groups'];expected.sort(key=lambda p:p['destination_start_sample'])
 assert len(pieces)==len(expected)==77
 fields=['source_part_id','source_file','source_file_sha256','source_local_start_sample','source_local_end_sample','destination_start_sample','destination_end_sample','pcm_sha256']
 assert[{k:p[k]for k in fields}for p in pieces]==[{k:p[k]for k in fields}for p in expected]
 raw=bytearray(SAMPLES*2);last_dest=0;last_source={p['part_id']:0 for p in parts};ranges={p['part_id']:[]for p in parts}
 for p in pieces:
  part=part_byid[p['source_part_id']];a,b=p['source_local_start_sample'],p['source_local_end_sample'];c,d=p['destination_start_sample'],p['destination_end_sample']
  assert p['source_file']==part['master']and p['source_file_sha256']==part['master_sha256']and 0<=last_source[part['part_id']]<=a<b<=part['samples']and last_dest<=c<d<=SAMPLES and b-a==d-c
  chunk=buffers[part['part_id']][a*2:b*2];assert sha(chunk)==p['pcm_sha256']and p['retained_pcm_exact']is True
  raw[c*2:d*2]=chunk;last_source[part['part_id']]=b;last_dest=d;ranges[part['part_id']].append((a,b))
 assert ranges['part1'][-1][1]==part_byid['part1']['samples']and ranges['part2'][0][0]==0 and ranges['part2'][-1][1]==part_byid['part2']['samples']
 slots={e['cut_id']:e for e in tl['entries']};assert[c['cut_id']for c in placement['cuts']]==ids
 for c in placement['cuts']:
  e=slots[c['cut_id']];assert c['cut_start_sample']==e['start_frame']*1600 and c['cut_end_sample']==e['end_frame']*1600 and c['cut_start_sample']<=c['speech_start_sample']<c['speech_end_sample']<=c['cut_end_sample']
 edits=placement['internal_quiet_edits'];assert len(edits)==len(plan['internal_pause_edits'])==10
 for e,q in zip(edits,plan['internal_pause_edits']):
  pid=e['source_part_id'];a,b=e['source_local_start_sample'],e['source_local_end_sample'];assert e['cut_id']==q['cut_id']and(a,b)==(q['remove_source_local_start_sample'],q['remove_source_local_end_sample'])and b-a==e['removed_samples']and sha(buffers[pid][a*2:b*2])==e['removed_pcm_sha256']==q['removed_pcm_sha256']
  lo,hi=q['source_local_quiet_start_sample'],q['source_local_quiet_end_sample'];assert lo+3840<=a<b<=hi-3840
  assert not any(w['start']*48000<b and w['end']*48000>a for w in asrs[pid])
  samples=array.array('h',buffers[pid][lo*2:hi*2])
  if sys.byteorder!='little':samples.byteswap()
  peak=max(20*math.log10(max(math.sqrt(sum(v*v for v in samples[i:i+480])/len(samples[i:i+480]))/32768,1e-12))for i in range(0,len(samples),480))
  assert peak<=-48+1e-6 and not any(max(a,x)<min(b,y)for x,y in ranges[pid])
 assert sum(e['removed_samples']for e in edits)==placement['internal_quiet_removed_samples']==127679
 group=placement['audio_groups'][0];assert len(placement['audio_groups'])==1 and group['cut_ids']==['ending_cut1','ending_cut2']and group['audio_splices']==group['internal_quiet_removed_samples']==0
 assert group['original_interclause_quiet_source_local_end_sample']-group['original_interclause_quiet_source_local_start_sample']==18240 and group['original_interclause_quiet_source_local_start_sample']<group['visual_boundary_source_local_sample']<group['original_interclause_quiet_source_local_end_sample']
 assert placement['spoken_samples_removed']==0 and placement['speech_tempo']==1 and placement['reused_ending']is False and placement['all77_retained_pieces_PCM_exact']is True
 raw_data=(OUT/'narration-raw.wav').read_bytes();info,actual=wav(raw_data)
 assert info=={'sample_rate':48000,'channels':1,'sample_width':2,'sample_count':SAMPLES}and actual==raw and sha(raw)==placement['raw_output']['pcm_sha256']==plan['proposed_raw_narration_pcm_sha256_not_written']and sha(raw_data)==placement['raw_output']['sha256']==processing['raw_source_sha256']
 assert not any(raw[tl['entries'][-1]['start_frame']*3200:])
 music_data=read(processing['music_source']);music_info,music=wav(music_data);_,final_music=wav((OUT/'bgm-loop.wav').read_bytes())
 assert sha(music_data)==processing['music_source_sha256']and music_info=={'sample_rate':48000,'channels':2,'sample_width':2,'sample_count':15096000}and processing['music_zero_tail_samples']==24000 and final_music==music+bytes(24000*4)
 assert processing['speech_tempo']==1 and processing['pitch_cents']==315 and sha(read(processing['pitch_source']))==processing['pitch_source_sha256']
 return {'source_identity_sha256':source_id,'original_source_samples':offset,'sources':source_rows,'retained_source_pieces':77,'mapped_speech_cuts':68,'strict_internal_quiet_edits':10,'internal_quiet_removed_samples':127679,'continuous_ending_pair':True,'source_join_EOF_head0_preserved':True,'raw_pcm_sha256':sha(raw),'original_music_prefix_samples':15096000,'music_zero_tail_samples':24000,'pitch_cents':315,'raw_PCM_identity_is_separate_from_DSP_voice':True}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('archive',nargs='?',type=Path,default=OUT/export.ARCHIVE_NAME);ap.add_argument('--package-only',action='store_true');args=ap.parse_args();archive=args.archive.resolve()
 if not archive.exists():print(json.dumps({'status':'WAITING_FOR_FINAL_ARCHIVE','production_complete':False,'validation_performed':False,'reproduction_performed':False}));return 2
 package={'status':'IN_PROGRESS','revision':10,'checks':{},'tested_archive':{'file':str(archive),'bytes':archive.stat().st_size,'sha256':file_sha(archive)},'scope':'Final315s ZIP inventory/privacy, approved retime, two original sources and77 pre-DSP PCM pieces, final rate-one/+315cents processing. No new generation or full video production.'}
 repro={'status':'NOT_RUN','revision':10,'checks':{},'remote_generation_invoked':False,'whole_video_encode_repeated':False,'mux_or_playback_repeated':False};active=package
 def check(report,name,ok,details):
  report['checks'][name]={'pass':bool(ok),'details':details}
  if not ok:raise AssertionError(name)
 try:
  with zipfile.ZipFile(archive)as z:
   infos=z.infolist();names=[x.filename for x in infos if not x.is_dir()];invalid=[];seen={};collisions=[]
   for info in infos:
    name=info.filename;key=unicodedata.normalize('NFC',name.rstrip('/')).casefold()
    if not relative(name)or stat.S_ISLNK(info.external_attr>>16):invalid.append(name)
    if key in seen and seen[key]!=name:collisions.append([seen[key],name])
    seen[key]=name
   check(package,'safe_relative_paths_no_symlinks_or_collisions',not invalid and not collisions,{'invalid':invalid,'collisions':collisions})
   check(package,'unique_archive_members',len(names)==len(set(names)),{'files':len(names)})
   mdata=z.read('SOURCE_MANIFEST.json');manifest=json.loads(mdata);rows=manifest['files'];listed=[r['file']for r in rows]
   check(package,'exact_manifest_inventory',len(listed)==len(set(listed))and set(names)==set(listed)|{'SOURCE_MANIFEST.json'},{'listed':len(rows),'unlisted':sorted(set(names)-set(listed)-{'SOURCE_MANIFEST.json'})})
   mismatches=[];secrets=[];workspace_bad=[];before={};redactions={r['file']:r for r in manifest.get('export_redactions',[])};redacted=[]
   for row in rows:
    data=z.read(row['file'])
    if sha(data)!=row['sha256']or len(data)!=row['bytes']:mismatches.append(row['file'])
    secrets.extend(export.signed_hits(row['file'],data))
    if row['file'].startswith(export.SOURCE_PREFIX):
     rel=row['file'][len(export.SOURCE_PREFIX):];p=ROOT/rel
     if not p.is_file():workspace_bad.append({'file':rel,'reason':'missing'});continue
     raw=p.read_bytes();before[rel]=sha(raw)
     if before[rel]!=row['sha256']:
      item=redactions.get(row['file']);clean,fields=export.sanitized_export(row['file'],raw)
      if item and item['original_sha256']==before[rel]and item['packaged_sha256']==sha(clean)==row['sha256']and fields==item['removed_fields']:redacted.append(rel)
      else:workspace_bad.append({'file':rel,'reason':'unexpected_difference'})
   check(package,'all_member_sha256_and_sizes_match',not mismatches,{'files':len(rows),'mismatches':mismatches})
   check(package,'all_zip_member_crc_verified',True,{'members_read_to_eof':len(rows)+1,'method':'ZipExtFile verifies CRC on every complete member read.'})
   secrets.extend(export.signed_hits('SOURCE_MANIFEST.json',mdata));check(package,'signed_generation_url_residue_zero',not secrets,{'hits':secrets,'hit_count':len(secrets),'URL_values_printed':False})
   check(package,'workspace_source_exact_except_declared_URL_redactions',not workspace_bad,{'files':len(before),'redacted_files':redacted,'unexpected':workspace_bad})
   def read(name):
    assert relative(name)and export.SOURCE_PREFIX+name in names,'Missing/nonrelative input: '+str(name)
    return z.read(export.SOURCE_PREFIX+name)
   def src(name):return json.loads(read(name))
   def receipt(name):return json.loads(z.read('out/showcase-v10/'+name))
   tl=src('timeline.json');sp=src('spec.json');config=src('narration/ko.json');source=src('narration/two-part-sources.json');placement=src('narration/placement-manifest.json');processing=src('narration/audio-processing-manifest.json');snapshot=manifest['visual_snapshot'];plan=src(snapshot['approved_plan']);authorization=src(snapshot['retime_authorization'])
   check(package,'authorized_retime_and_two_source_metadata',manifest['revision']==10 and manifest['production_complete']is True and manifest['delivery_status']=='FINAL'and manifest['generation_mode']==source['generation_mode']==placement['generation_mode']=='two_part_with_user_authorization'and manifest['two_part_exception_authorized']is True and manifest['retime_exception_authorized']is True and manifest['speech_tempo']==source['speech_tempo']==placement['speech_tempo']==processing['speech_tempo']==1 and manifest['pitch_cents']==processing['pitch_cents']==315 and snapshot['source_design_revision']==9 and snapshot['effective_timeline_revision']==10 and snapshot['old_audio_references_are_not_current_provenance']is True and sha(read('spec.json'))==snapshot['spec_sha256']==export.SPEC_SHA and sha(read('timeline.json'))==snapshot['timeline_sha256']and sha(read(snapshot['baseline_timeline_file']))==snapshot['baseline_timeline_sha256']==export.BASELINE_TIMELINE_SHA and snapshot['prior_silent_video_sha256']==export.BASELINE_SILENT_SHA and sha(read(snapshot['approved_plan']))==snapshot['approved_plan_sha256']==authorization['approved_proposal_sha256']and sha(read(snapshot['retime_authorization']))==snapshot['retime_authorization_sha256']and geometry(tl['entries'])==geometry(plan['entries']),{'source_design_revision':9,'actual_timeline_revision':10,'two_sources':True,'retime_authorization_sha256':snapshot['retime_authorization_sha256'],'speech_tempo':1,'pitch_cents':315})
   sections=list(dict.fromkeys(e['section_id']for e in tl['entries']));tasks=[s for s in sp['sections']if s['type']=='task'];ids=[c['id']for b in config['blocks']for c in b['cuts']]
   shape=tl['revision']==10 and tl['preview_only']is False and(tl['fps'],tl['frames'],tl['duration'])==(30,9450,315)and len(tl['entries'])==69 and all(e['kind']!='title'for e in tl['entries'])and sections==ORDER and[e['cut_index']for e in tl['entries']if e['section_id']=='ending']==[0,1,2,4,5]and{s['id']:len(s['cuts'])for s in tasks}==COUNTS and len(config['blocks'])==14 and len(ids)==68 and[c for p in source['parts']for c in p['cut_ids']]==ids and tl['entries'][-1]['start_frame']==9330 and tl['entries'][-1]['end_frame']==9450
   check(package,'approved69_visual_entries_68_spoken_cuts_and4s_card',shape,{'duration':315,'frames':9450,'entries':69,'spoken_cuts':len(ids),'source_part_counts':[len(p['cut_ids'])for p in source['parts']]})
   required=['README.md','package-source.py','verify-source-package.py','render.mjs','stage.mjs','task-scenes.js','hero-scenes.js','task-visuals-early.js','task-visuals-late.js','photo-camera.js','photo-camera-profiles.json','audio.py','place-narration-v10.py','mix-v10-audio.py','pitch-narration.swift','finish.py','validate-final.py','review-encoded-audio.py','export-narration-timeline.py','fonts/NotoSansCJKkr-Regular.otf','fonts/NotoSansCJKkr-Bold.otf','narration/two-part-sources.json','narration/placement-manifest.json','narration/audio-processing-manifest.json','narration/retime-tone-authorization.json','narration/retime/approved-plan.json','baseline/timeline-revision9.json']
   missing=[p for p in required if export.SOURCE_PREFIX+p not in names];check(package,'required_standalone_runtime_present',not missing,{'files':len(required),'missing':missing})
   final=receipt('final-validation.json');mux=receipt('mux-validation.json');state=receipt('SOURCE_STATUS.json');render=receipt('render-validation.json');audio=receipt('audio-validation.json');dsp=receipt('dsp-validation.json');native=receipt('retime-native-visual-review.json');silent=receipt('silent-encoded-visual-review.json')
   current=OUT/export.VIDEO_NAME;video_sha=file_sha(current)if current.exists()else None;output_identity={n:wav_identity(OUT/n)for n in WAV_NAMES};output_bad=[]
   for n,v in output_identity.items():
    expected=audio['files'][n]
    if v['sha256']!=expected['sha256']or v['sample_count']!=expected['samples']or v['sample_rate']!=expected['sample_rate']or v['channels']!=expected['channels']or processing['outputs'][n]!=expected:output_bad.append(n)
   receipt_bad=[];checked_receipts=set()
   def check_linked_receipts(value,owner):
    for item in value.get('receipts',[]):
     assert relative(item['file']),'Nonrelative linked receipt: '+owner
     name='out/showcase-v10/'+item['file'];actual=sha(z.read(name));red=redactions.get(name)
     if actual!=item['sha256']and not(red and red['original_sha256']==item['sha256']and red['packaged_sha256']==actual):receipt_bad.append({'owner':owner,'file':name})
     if name not in checked_receipts:
      checked_receipts.add(name);check_linked_receipts(json.loads(z.read(name)),name)
   check_linked_receipts(final,'final-validation.json')
   check(package,'current_final_media_receipts_and_four_wavs_bound',all(passing(r)for r in [final,mux,render,audio,dsp,native,silent])and final.get('production_complete')is True and not final.get('preview_only',False) and state.get('revision')==10 and state.get('production_complete')is True and video_sha==manifest['final_video_sha256']==export.video_hash(final)==export.video_hash(mux)and video_sha is not None and render['sha256']==snapshot['silent_video_sha256']==silent['video_sha256']and not output_bad and not receipt_bad,{'video_sha256':video_sha,'silent_video_sha256':render['sha256'],'wav_mismatches':output_bad,'receipt_hash_mismatches':receipt_bad,'raw_and_pitch_processed_audio_are_distinct':True})
   bound={r['file']:r['sha256']for r in render['inputs']};bound.update(export.bindings(audio));bound.update(export.bindings(placement));bad=[p for p,h in bound.items()if not relative(p)or export.SOURCE_PREFIX+p not in names or sha(read(p))!=h];active_audio=manifest['active_audio'];active_bad=[]
   for key in ['source_manifest','placement_manifest','processing_manifest']:
    if sha(read(active_audio[key]))!=active_audio[key+'_sha256']:active_bad.append(key)
   check(package,'relative_active_inputs_and_DSP_source_identity_bound',bool(bound)and not bad and not active_bad and placement['source_identity_sha256']==audio['source_identity_sha256']==processing['source_identity_sha256']==active_audio['source_identity_sha256']and placement['timeline_sha256']==processing['timeline_sha256']==sha(read('timeline.json'))and processing['placement_manifest_sha256']==sha(read('narration/placement-manifest.json'))and render['timeline_file']=='timeline.json'and render['preview_only']is False,{'bindings':len(bound),'invalid':bad,'active_metadata_mismatches':active_bad})
   pcm=check_pcm(read,source,placement,config,tl,processing)
   check(package,'two_original_sources_77_exact_raw_pieces_and_separate_DSP',placement['status']=='PASS_RAW_PCM_PLACEMENT'and pcm['raw_pcm_sha256']==output_identity['narration-raw.wav']['pcm_sha256']and dsp['status']=='PASS'and dsp['pitch_cents']==315 and dsp['speech_tempo']==1 and dsp['source_raw_sha256']==output_identity['narration-raw.wav']['sha256']and dsp['aligned_samples']==SAMPLES and dsp['final_card_raw_literal_zero']is True and dsp['final_card_after_50ms_literal_zero']is True and dsp['processor_tail_was_not_cut_or_faded']is True,{'proof':pcm,'DSP_validation_sha256':sha(z.read('out/showcase-v10/dsp-validation.json')),'final_card_voice_processor_tail_ms':dsp['final_card_processor_tail_ms'],'subjective_tone_acceptance_claimed':False})
   assets={s['reference_image']for s in sp['sections']if s.get('reference_image')};assets.update(p for s in sp['sections']for p in s.get('backgrounds',[])if p);assets.update(sp.get('microscopy',{}).values());assets.update(f'assets/opening/cut{i:02d}.png'for i in range(1,10));missing=[p for p in assets if not relative(p)or export.SOURCE_PREFIX+p not in names]
   check(package,'all_native_assets_in_archive',not missing,{'assets':len(assets),'missing':missing});assert len(package['checks'])==14
   ident=export.source_identity(rows);assert ident==manifest['immutable_source_identity'];package.update(status='PASS',immutable_source_identity=ident,source_manifest_sha256=sha(mdata),archive_file_count=len(names))
   prior=OUT/'source-reproduction-validation.json'
   if args.package_only and prior.exists():
    old=json.loads(prior.read_text())
    if old.get('status')=='SOURCE_PASS':assert old['immutable_source_identity']==ident;package['same_immutable_source_as_fresh_reproduction']=True
   save(OUT/'source-package-validation.json',package)
   if args.package_only:print(json.dumps({'status':'PASS','checks':14,'archive_sha256':package['tested_archive']['sha256'],'immutable_source_identity':ident}));return 0
   temp=Path(tempfile.mkdtemp(prefix='media-maker-v10-source-smoke-',dir='/private/tmp'));z.extractall(temp)
  active=repro;extracted=temp/'showcase-v10';tempout=temp/'out/showcase-v10';source_rows=[r for r in rows if r['file'].startswith(export.SOURCE_PREFIX)];expected_png=manifest['native_png_sha256']
  repro.update(tested_archive=package['tested_archive'],immutable_source_identity=ident,source_manifest_sha256=package['source_manifest_sha256'],extraction_directory=str(temp),source_identity_sha256=placement['source_identity_sha256'])
  check(repro,'fresh_private_extraction_without_previous_projects',not any((temp/f'showcase-v{i}').exists()for i in range(1,10)),{'directory':str(temp)})
  check(repro,'all_extracted_sources_match_archive',all(file_sha(temp/r['file'])==r['sha256']for r in source_rows),{'files':len(source_rows)})
  check(repro,'canonical_expected69png_and4wav_records',len(expected_png)==69 and expected_png=={p.name:file_sha(p)for p in(OUT/'stills').glob('*.png')}and len(output_identity)==4 and all(v['sample_rate']==48000 and v['sample_count']==SAMPLES for v in output_identity.values()),{'native_pngs':len(expected_png),'wavs':output_identity})
  env=os.environ.copy();env['TIMELINE_FILE']='timeline.json'
  for key in ['RENDER_FILE','RENDER_REPORT','SHOWCASE_OUT','SHOWCASE_VIDEO']:env.pop(key,None)
  node=os.environ.get('NODE_BINARY','node');node_version=subprocess.check_output([node,'--version'],text=True).strip();log=OUT/'source-reproduction-render.log'
  with log.open('w')as f:run=subprocess.run([node,'render.mjs','--stills'],cwd=extracted,env=env,stdout=f,stderr=subprocess.STDOUT)
  check(repro,'saved_actual_native_render_succeeded',run.returncode==0,{'return_code':run.returncode,'node_version':node_version,'command':'TIMELINE_FILE=timeline.json node render.mjs --stills','log':str(log)})
  png={p.name:file_sha(p)for p in(tempout/'stills').glob('*.png')};bad=[p for p in set(png)|set(expected_png)if png.get(p)!=expected_png.get(p)]
  check(repro,'all69_native_pngs_byte_identical',len(png)==69 and not bad,{'actual':len(png),'mismatches':sorted(bad)})
  visual=json.loads((tempout/'visual-validation.json').read_text());check(repro,'native69_motion_probes_and_no_captions',visual['status']=='PASS'and len(visual['records'])==69 and len(visual['motion'])==69 and all(x['moving']for x in visual['motion'])and all(not x['caption']for x in visual['records']),{'records':len(visual['records']),'motion':len(visual['motion'])})
  python=os.environ.get('AUDIO_PYTHON',str(BUNDLED)if BUNDLED.exists()else sys.executable);log=OUT/'source-reproduction-audio.log'
  with log.open('w')as f:run=subprocess.run([python,'audio.py'],cwd=extracted,env=env,stdout=f,stderr=subprocess.STDOUT)
  check(repro,'saved_input_raw_plus_offline_DSP_audio_build_succeeded',run.returncode==0,{'return_code':run.returncode,'python':python,'command':'python3 audio.py','log':str(log),'ffmpeg_version':subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0],'network_or_hardware_audio_requested':False})
  actual={n:wav_identity(tempout/n)for n in WAV_NAMES};check(repro,'four_wav_file_and_pcm_hashes_exact',actual==output_identity,{'expected':output_identity,'reproduced':actual})
  rebuilt=json.loads((tempout/'audio-validation.json').read_text());check(repro,'rebuilt_audio_identity_and_bindings_pass',passing(rebuilt)and rebuilt['source_identity_sha256']==placement['source_identity_sha256']and all(relative(p)and file_sha(extracted/p)==h for p,h in export.bindings(rebuilt).items()),{'status':rebuilt['status'],'bindings':len(export.bindings(rebuilt))})
  changed=[r['file']for r in source_rows if file_sha(temp/r['file'])!=r['sha256']];check(repro,'archived_source_files_unchanged_by_reproduction',not changed,{'files':len(source_rows),'changed':changed})
  changed=[p for p,h in before.items()if file_sha(ROOT/p)!=h];check(repro,'original_source_and_reference_outputs_unchanged',not changed and output_identity=={n:wav_identity(OUT/n)for n in WAV_NAMES}and expected_png=={p.name:file_sha(p)for p in(OUT/'stills').glob('*.png')},{'source_files':len(before),'changed':changed})
  repro.update(status='SOURCE_PASS',native_png_hashes=png,audio_outputs=actual,limitations=['Source69 PNG and fourWAV reproduction only; no whole-video encode, mux, browser playback or subjective listening repeated.','Two untouched originals are the authorized source. Pre-DSP raw PCM proof is separate from rate-one/+315cents and constant-gain processing.','Offline macOS Swift/AVAudioUnit reproduction requires local CoreAudio component access, without microphone, speaker or network use.']);save(OUT/'source-reproduction-validation.json',repro)
  print(json.dumps({'package_status':'PASS','package_checks':14,'reproduction_status':'SOURCE_PASS','reproduction_checks':len(repro['checks']),'png_matches':69,'wav_file_matches':4,'pcm_matches':4,'archive_sha256':package['tested_archive']['sha256'],'immutable_source_identity':ident}));return 0
 except Exception as e:
  active.update(status='FAIL',error={'type':type(e).__name__,'check':str(e)});save(OUT/'source-package-validation.json',package)
  if active is repro:save(OUT/'source-reproduction-validation.json',repro)
  print(json.dumps({'status':'FAIL','type':type(e).__name__,'check':str(e)}));return 1
if __name__=='__main__':raise SystemExit(main())
