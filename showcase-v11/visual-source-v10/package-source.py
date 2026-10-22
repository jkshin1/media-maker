#!/usr/bin/env python3
"""Prepare a standalone Revision10 source archive after final media approval.

Default invocation only checks readiness. --final explicitly writes the archive.
No rendering, speech generation, audio mixing or source mutation occurs here.
"""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,re,urllib.parse,zipfile

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'out/showcase-v10'
SOURCE_PREFIX='showcase-v10/'
ARCHIVE_NAME='RD_Process_AI_Fast_Track_Showcase_Revision10_Source.zip'
VIDEO_NAME='RD_Process_AI_Fast_Track_Showcase_Revision10.mp4'
BASELINE_SILENT_SHA='100e4e137823a79427a8908cc240a364cfc63a18e7c682d241edd03980d24c73'
BASELINE_TIMELINE_SHA='03c984a6d5b29b3be07a29669d76c3bc25cdde23da9b0ac9789b3dea73cbb68b'
SPEC_SHA='0f6a3caf04d1d82a728f476b21c166fa225f2cd113c57cd27e92185378d19345'
SIGNED_KEYS={'x-amz-signature','x-amz-credential','x-amz-security-token','x-goog-signature','x-goog-credential','signature','sig','token','access_token','authorization','jwt','key-pair-id','policy'}
TEXT_EXT={'.json','.txt','.md','.py','.js','.mjs','.cjs','.html','.css','.toml','.yaml','.yml','.csv','.srt','.vtt','.log'}
EXCLUDED_RECEIPTS={'source-package-validation.json','delivery-validation.json'}

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def relative(value):
 return isinstance(value,str)and bool(value)and '\\'not in value and '\0'not in value and not PurePosixPath(value).is_absolute()and '..'not in PurePosixPath(value).parts and not re.match(r'^[A-Za-z]:',value)
def load(path):return json.loads(Path(path).read_text())
def passing(value):
 if value.get('status')not in {'PASS','PASS_WITH_ASR_VARIANTS'}:return False
 checks=value.get('checks')
 if checks is None:return True
 items=checks.values()if isinstance(checks,dict)else checks
 return bool(checks)and all(x is True or isinstance(x,dict)and(x.get('pass')is True or x.get('status')=='PASS')for x in items)
def video_hash(value):return value.get('final_sha256',value.get('video_sha256',value.get('sha256')))
def bindings(value):
 b=value.get('input_bindings',value.get('inputs',{}))
 return b if isinstance(b,dict)else {x['file']:x['sha256']for x in b}
def source_identity(rows):
 values=[{k:r[k]for k in ('file','sha256','bytes')}for r in rows if r['file'].startswith(SOURCE_PREFIX)]
 data=json.dumps(sorted(values,key=lambda r:r['file']),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
 return {'file_count':len(values),'manifest_sha256':sha(data)}
def signed_hits(name,data):
 """Return paths/query-key names only. Never include URL values in reports."""
 try:text=data.decode('utf-8')
 except UnicodeDecodeError:
  # Binary assets are never rewritten. Reject any embedded signed URL rather
  # than overlooking textual metadata inside a WAV/image/container.
  hits=[]
  for value in re.findall(rb'https?://[^\s\"\'<>\x00-\x20]{1,16384}',data):
   hits.extend(signed_hits(name,value.decode('utf-8','replace').encode()))
  return hits
 strings=[]
 def walk(v,key='$'):
  if isinstance(v,dict):
   for k,x in v.items():walk(x,key+'.'+str(k))
  elif isinstance(v,list):
   for i,x in enumerate(v):walk(x,f'{key}[{i}]')
  elif isinstance(v,str):strings.append((key,v))
 try:walk(json.loads(text))
 except(ValueError,TypeError):strings=[('$text',text)]
 hits=[]
 for key,value in strings:
  value=value.replace('\\/','/').replace('&amp;','&')
  for _ in range(2):
   decoded=urllib.parse.unquote(value)
   if decoded==value:break
   value=decoded
  for url in re.findall(r'https?://[^\s\"\'<>]+',value,re.I):
   pairs=urllib.parse.parse_qsl(urllib.parse.urlsplit(url.rstrip('),.;]')).query,keep_blank_values=True)
   keys=sorted({k for k,_ in pairs if k.lower()in SIGNED_KEYS or k.lower().startswith(('x-amz-','x-goog-'))})
   if keys:hits.append({'file':name,'key_path':key,'parameter_keys':keys})
  if re.search(r'X-(?:Amz|Goog)-Signature\s*(?:=|%3D)',value,re.I)and not any(x['key_path']==key for x in hits):hits.append({'file':name,'key_path':key,'parameter_keys':['signature-marker']})
 return hits
def sanitized_export(name,data):
 """Redact signed-media URL values in exported copies, preserving originals."""
 fields=[];generation_record='/narration/'in '/'+name and any(x in Path(name).name.lower()for x in ['generation','receipt'])
 if Path(name).suffix.lower()=='.json':
  original=json.loads(data)
  def clean(v,key='$'):
   if isinstance(v,dict):
    result={}
    for k,x in v.items():
     if generation_record and (k.lower()=='url'or k.lower().endswith('_url'))and isinstance(x,str)and re.search(r'https?://',x):fields.append(key+'.'+k);continue
     result[k]=clean(x,key+'.'+k)
    return result
   if isinstance(v,list):return [clean(x,f'{key}[{i}]')for i,x in enumerate(v)]
   if isinstance(v,str)and signed_hits(name,v.encode()):fields.append(key);return '[SIGNED_GENERATION_URL_REMOVED]'
   return v
  result=clean(original)
  if fields:data=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
 elif Path(name).suffix.lower()in TEXT_EXT:
  try:text=data.decode('utf-8')
  except UnicodeDecodeError:text=None
  if text is not None:
   lines=text.splitlines(keepends=True)
   for i,line in enumerate(lines):
    if signed_hits(name,line.encode()):lines[i]='[SIGNED_GENERATION_URL_REMOVED]'+ ('\n'if line.endswith('\n')else '');fields.append(f'$text_line[{i+1}]')
   if fields:data=''.join(lines).encode()
 return data,fields

def approved_visual_contract():
 auth_file='narration/retime-tone-authorization.json';auth=load(ROOT/auth_file);plan_file=auth['approved_proposal'];plan_data=(ROOT/plan_file).read_bytes();plan=json.loads(plan_data);tl=load(ROOT/'timeline.json')
 assert auth['authorization_source']=='direct_user_reply_in_current_chat'and auth['speech_tempo']==1 and auth['pitch_cents']==315 and sha(plan_data)==auth['approved_proposal_sha256'],'Approved retime/tone binding changed.'
 assert (tl['revision'],tl['fps'],tl['frames'],tl['duration'],len(tl['entries']))==(10,30,9450,315,69)and tl['preview_only']is False,'Effective Revision10 timing is not approved315 seconds.'
 fields=['section_id','kind','cut_id','cut_index','start_frame','end_frame','start','end','caption']
 geometry=lambda entries:[{k:e[k]for k in fields}for e in entries]
 assert geometry(tl['entries'])==geometry(plan['entries']),'Effective timing differs from approved plan.'
 assert file_sha(ROOT/'spec.json')==SPEC_SHA and file_sha(ROOT/'baseline/timeline-revision9.json')==BASELINE_TIMELINE_SHA,'Design/baseline snapshot changed.'
 return {'source_design_revision':9,'spec_file':'spec.json','spec_sha256':SPEC_SHA,'baseline_timeline_file':'baseline/timeline-revision9.json','baseline_timeline_sha256':BASELINE_TIMELINE_SHA,'prior_silent_video_sha256':BASELINE_SILENT_SHA,'effective_timeline_revision':10,'timeline_file':'timeline.json','timeline_sha256':file_sha(ROOT/'timeline.json'),'retime_authorization':auth_file,'retime_authorization_sha256':file_sha(ROOT/auth_file),'approved_plan':plan_file,'approved_plan_sha256':sha(plan_data),'old_audio_references_are_not_current_provenance':True}

def final_ready():
 required=['SOURCE_STATUS.json','final-validation.json','mux-validation.json','audio-validation.json','raw-placement-validation.json','dsp-validation.json','render-validation.json','final-speech-validation.json','encoded-audio-validation.json','encoded-visual-review.json','playback-validation.json','retime-native-visual-review.json','silent-encoded-visual-review.json']
 missing=[name for name in required if not(OUT/name).exists()]
 for name in ['narration/two-part-sources.json','narration/placement-manifest.json','narration/audio-processing-manifest.json','narration/two-parts/authorization.json','narration/retime-tone-authorization.json']:
  if not(ROOT/name).exists():missing.append(name)
 if not(OUT/VIDEO_NAME).exists():missing.append(VIDEO_NAME)
 if missing:raise AssertionError('Final prerequisites missing: '+', '.join(missing))
 final=load(OUT/'final-validation.json');state=load(OUT/'SOURCE_STATUS.json');mux=load(OUT/'mux-validation.json');audio=load(OUT/'audio-validation.json');render=load(OUT/'render-validation.json');placement=load(ROOT/'narration/placement-manifest.json');authorization=load(ROOT/'narration/two-parts/authorization.json')
 assert passing(final)and final.get('production_complete')is True and not final.get('preview_only',False),'Final media validation is not complete.'
 assert state.get('revision')==10 and state.get('production_complete')is True,'Source status is not production-complete Revision10.'
 actual=file_sha(OUT/VIDEO_NAME)
 assert video_hash(final)==video_hash(mux)==actual and passing(mux),'Final receipts do not bind the current MP4.'
 assert all(passing(load(OUT/name))for name in required if name not in {'SOURCE_STATUS.json','raw-placement-validation.json'}),'A required scoped receipt has not passed.'
 for name in required:
  for item in load(OUT/name).get('receipts',[]):
   assert relative(item['file'])and(OUT/item['file']).is_file()and file_sha(OUT/item['file'])==item['sha256'],'A linked receipt is stale: '+name+' -> '+str(item.get('file'))
 visual=approved_visual_contract();provenance=render['retime_provenance']
 assert file_sha(OUT/'video_silent.mp4')==render['sha256']and render['status']=='PASS'and(render['frames'],render['duration'])==(9450,315),'Approved visual render changed.'
 assert provenance['authorization_sha256']==visual['retime_authorization_sha256']and provenance['approved_plan_sha256']==visual['approved_plan_sha256'],'Renderer belongs to a different authorization.'
 assert all(file_sha(ROOT/item['file'])==item['sha256']for item in render['inputs']),'A render input changed after encoding.'
 assert authorization.get('generation_mode')=='two_part_with_user_authorization'and authorization.get('speech_speed_ratio')==1,'Two-part generation is not authorized.'
 assert placement.get('status')=='PASS_RAW_PCM_PLACEMENT'and len(placement.get('source_parts',[]))==2 and len(placement.get('cuts',[]))==68 and len(placement.get('pieces',[]))==77,'Actual approved raw placement is not complete.'
 assert placement['approved_plan_sha256']==visual['approved_plan_sha256']and placement['timeline_sha256']==visual['timeline_sha256']and placement['retime_authorization_sha256']==visual['retime_authorization_sha256'],'Raw placement uses different approved timing.'
 assert placement.get('speech_tempo')==1 and audio.get('speech_tempo')==1 and passing(audio),'Speech tempo or audio validation is not approved.'
 assert placement.get('source_identity_sha256')and placement['source_identity_sha256']==audio.get('source_identity_sha256'),'Audio source identities differ.'
 assert bindings(audio)and all(relative(p)and(ROOT/p).is_file()and file_sha(ROOT/p)==h for p,h in bindings(audio).items()),'Audio runtime paths/hashes are not portable.'
 visual['silent_video_sha256']=render['sha256'];processing=load(ROOT/'narration/audio-processing-manifest.json')
 assert processing['source_identity_sha256']==placement['source_identity_sha256']and processing['timeline_sha256']==visual['timeline_sha256'],'DSP processing uses different sources/timing.'
 assert processing['placement_manifest_sha256']==file_sha(ROOT/'narration/placement-manifest.json'),'DSP processing uses a different pre-DSP placement.'
 assert processing['speech_tempo']==1 and processing['pitch_cents']==315 and processing['music_zero_tail_samples']==24000,'Final DSP parameters changed.'
 assert processing['outputs']==audio['files'],'Processing and final audio output identities differ.'
 for name,identity in audio['files'].items():
  assert name in {'audio.wav','narration.wav','narration-raw.wav','bgm-loop.wav'} and identity['samples']==15120000 and file_sha(OUT/name)==identity['sha256'],'Current four-WAV identity changed.'
 return {'final_video_sha256':actual,'placement':placement,'processing':processing,'visual':visual,'audio':audio,'source_parts':load(ROOT/'narration/two-part-sources.json')}

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--final',action='store_true',help='Write the final archive only after all final-media gates pass.');args=parser.parse_args()
 try:ready=final_ready()
 except(AssertionError,KeyError,FileNotFoundError)as e:
  print(json.dumps({'status':'WAITING_FOR_FINAL_VALIDATION','production_complete':False,'archive_written':False,'reason':str(e)},ensure_ascii=False));return 2
 if not args.final:
  print(json.dumps({'status':'READY_FOR_EXPLICIT_FINAL_PACKAGING','archive_written':False}));return 0
 rows=[];payloads={};redactions=[]
 paths=[]
 for path in sorted(ROOT.rglob('*')):
  rel=path.relative_to(ROOT)
  if any(x in {'node_modules','__pycache__','.DS_Store'}or x.startswith('.')for x in rel.parts):continue
  assert not path.is_symlink(),'Symlinks are not exported: '+str(rel)
  if path.is_file():paths.append((SOURCE_PREFIX+rel.as_posix(),path,'source'))
 paths.extend(('out/showcase-v10/'+p.name,p,'scoped_validation_receipt')for p in sorted(OUT.glob('*.json'))if p.name not in EXCLUDED_RECEIPTS)
 # Keep the actual processed-voice transcript portable without rewriting the
 # immutable speech/mux receipts that bind its original absolute capture path.
 for path in sorted((OUT/'final-voice-transcription').glob('*.json')):
  paths.append(('out/showcase-v10/'+path.relative_to(OUT).as_posix(),path,'processed_voice_transcript'))
 for path in sorted(OUT.glob('*.md')):
  paths.append(('out/showcase-v10/'+path.name,path,'narration_or_scope_document'))
 for name,path,kind in paths:
  raw=path.read_bytes();data,fields=sanitized_export(name,raw)
  assert not signed_hits(name,data),'Unredacted signed URL remains in '+name
  if fields:redactions.append({'file':name,'original_sha256':sha(raw),'packaged_sha256':sha(data),'removed_fields':fields})
  payloads[name]=data;rows.append({'file':name,'sha256':sha(data),'bytes':len(data),'kind':kind})
 active=bindings(ready['audio'])|bindings(ready['placement'])
 for name,expected in active.items():
  assert relative(name)and SOURCE_PREFIX+name in payloads and sha(payloads[SOURCE_PREFIX+name])==expected,'An active runtime input would change during export: '+str(name)
 ident=source_identity(rows);prior=OUT/'source-reproduction-validation.json'
 if prior.exists()and load(prior).get('status')=='SOURCE_PASS':assert load(prior)['immutable_source_identity']==ident,'Source changed after fresh reproduction; do not reuse its receipt.'
 pngs={p.name:file_sha(p)for p in sorted((OUT/'stills').glob('*.png'))};assert len(pngs)==69,'Current native69 PNGs are required.'
 manifest={'revision':10,'production_complete':True,'delivery_status':'FINAL','human_acceptance':'PENDING_USER_REVIEW','duration_seconds':315,'frames':9450,'max_seconds':315,'generation_mode':'two_part_with_user_authorization','two_part_exception_authorized':True,'retime_exception_authorized':True,'speech_tempo':1,'pitch_cents':315,'final_video_sha256':ready['final_video_sha256'],'visual_snapshot':ready['visual'],'native_png_sha256':pngs,'active_audio':{'source_manifest':'narration/two-part-sources.json','source_manifest_sha256':sha(payloads[SOURCE_PREFIX+'narration/two-part-sources.json']),'placement_manifest':'narration/placement-manifest.json','placement_manifest_sha256':sha(payloads[SOURCE_PREFIX+'narration/placement-manifest.json']),'processing_manifest':'narration/audio-processing-manifest.json','processing_manifest_sha256':sha(payloads[SOURCE_PREFIX+'narration/audio-processing-manifest.json']),'source_identity_sha256':ready['placement']['source_identity_sha256']},'immutable_source_identity':ident,'signed_generation_urls_omitted':True,'export_redactions':redactions,'files':rows}
 target=OUT/ARCHIVE_NAME;temporary=target.with_suffix('.partial.zip')
 with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for name,data in payloads.items():z.writestr(name,data)
  z.writestr('SOURCE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 with zipfile.ZipFile(temporary)as z:assert z.testzip()is None,'ZIP CRC failure.'
 temporary.replace(target)
 print(json.dumps({'status':'PACKAGED_FINAL','file':str(target),'bytes':target.stat().st_size,'sha256':file_sha(target),'files':len(rows),'immutable_source_identity':ident,'redacted_files':len(redactions)}));return 0
if __name__=='__main__':raise SystemExit(main())
