#!/usr/bin/env python3
"""Package the locked-video/natural-pitch Revision11 after final approval.

Default invocation checks readiness; --final writes the final source archive.
No audio build, remote generation, video encoding or source mutation occurs.
"""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,re,urllib.parse,zipfile
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'out/showcase-v11'
SOURCE_PREFIX='showcase-v11/'
ARCHIVE_NAME='RD_Process_AI_Fast_Track_Showcase_Revision11_Source.zip'
VIDEO_NAME='RD_Process_AI_Fast_Track_Showcase_Revision11.mp4'
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
 return isinstance(value,str)and bool(value)and '\\'not in value and '\0'not in value and not PurePosixPath(value).is_absolute()and PurePosixPath(value).as_posix()==value and '..'not in PurePosixPath(value).parts and not re.match(r'^[A-Za-z]:',value)
def load(path):return json.loads(Path(path).read_text())
def passing(value):
 if value.get('status')not in {'PASS','PASS_WITH_ASR_VARIANTS','PASS_INDEPENDENT_AUDIO_PCM','PASS_SOURCE_SPEECH_PRESERVATION'}:return False
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

# Active Revision11 runtime contract.
REQUIRED_RECEIPTS=['final-validation.json','mux-validation.json','audio-validation.json','independent-audio-validation.json','speech-preservation-validation.json','encoded-audio-validation.json','visual-preservation-validation.json','SOURCE_STATUS.json']
WAV_NAMES=['audio.wav','narration.wav','narration-raw.wav','bgm-loop.wav']

def snapshot_check(read,baseline,redactions=None):
 redactions=redactions or {};differences=[];redacted=[]
 for row in baseline['source_files']:
  name=baseline['snapshot_directory']+'/'+row['file'];data=read(name)
  if sha(data)!=row['sha256']or len(data)!=row['bytes']:
   item=redactions.get(SOURCE_PREFIX+name)
   if item and item['original_sha256']==row['sha256']and item['packaged_sha256']==sha(data)and item['removed_fields']:redacted.append(name)
   else:differences.append(name)
 assert len(baseline['source_files'])==172 and not differences,'Historical snapshot changed: '+str(differences)
 return {'source_files':172,'exact_files':172-len(redacted),'URL_redacted_export_copies':redacted,'baseline_revision':10}

def final_ready():
 missing=[n for n in REQUIRED_RECEIPTS if not(OUT/n).is_file()]
 for n in ['audio.py','finish.py','authorization.json','baseline-provenance.json','timeline.json','audio-processing-manifest.json','assets/video/locked-silent.mp4']:
  if not(ROOT/n).is_file():missing.append(n)
 if not(OUT/VIDEO_NAME).is_file():missing.append(VIDEO_NAME)
 assert not missing,'Final prerequisites missing: '+', '.join(missing)
 reports={n:load(OUT/n)for n in REQUIRED_RECEIPTS};final=reports['final-validation.json'];state=reports['SOURCE_STATUS.json'];mux=reports['mux-validation.json'];audio=reports['audio-validation.json'];processing=load(ROOT/'audio-processing-manifest.json');baseline=load(ROOT/'baseline-provenance.json');auth=load(ROOT/'authorization.json');tl=load(ROOT/'timeline.json')
 assert all(passing(r)for n,r in reports.items()if n!='SOURCE_STATUS.json'),'A required final receipt has not passed.'
 assert final.get('production_complete')is True and state.get('production_complete')is True and state.get('revision')==11,'Revision11 production is not complete.'
 current=file_sha(OUT/VIDEO_NAME);assert video_hash(final)==video_hash(mux)==current,'Final media hash differs.'
 assert auth['authorization_source']=='direct_user_request_in_current_chat'and auth['pitch_shift_cents']==0 and auth['pitch_or_time_processor_allowed']is False and auth['speech_tempo']==1 and auth['new_remote_generation_authorized']is False,'Natural-pitch authorization differs.'
 assert file_sha(ROOT/'timeline.json')==file_sha(ROOT/'visual-source-v10/timeline.json')==baseline['timeline_sha256']and(tl['frames'],tl['duration'],len(tl['entries']))==(9450,315,69),'Timeline differs.'
 assert file_sha(ROOT/baseline['locked_silent_file'])==baseline['locked_silent_sha256'],'Locked video differs.'
 snapshot_check(lambda p:(ROOT/p).read_bytes(),baseline)
 assert len([p for p in(ROOT/'visual-source-v10').rglob('*')if p.is_file()and '__pycache__'not in p.parts and not any(x.startswith('.')for x in p.relative_to(ROOT/'visual-source-v10').parts)])==172,'Unexpected historical source inventory.'
 assert processing['revision']==11 and processing['pitch_cents']==audio['pitch_cents']==0 and processing['speech_tempo']==audio['speech_tempo']==1,'Active audio uses different pitch/tempo.'
 for key in ['no_pitch_processor','no_time_processor','no_filter_or_EQ_or_compressor','no_new_speech_generation']:
  assert processing[key]is True and audio[key]is True,'Unexpected processing: '+key
 assert processing['files']==audio['files']and set(processing['files'])==set(WAV_NAMES),'Four-WAV identities differ.'
 for name,value in processing['files'].items():assert file_sha(OUT/name)==value['sha256']and value['samples']==15120000,'A WAV changed: '+name
 assert bindings(processing)==bindings(audio)and all(relative(p)and(ROOT/p).is_file()and file_sha(ROOT/p)==h for p,h in bindings(processing).items()),'Active inputs are not relative/current.'
 for owner,r in reports.items():
  for item in r.get('receipts',[]):
   assert relative(item['file'])and(OUT/item['file']).is_file()and file_sha(OUT/item['file'])==item['sha256'],'Stale receipt: '+owner+' -> '+str(item.get('file'))
 reference=load(ROOT/'baseline-reviews/encoded-visual-review.json')['video_stream_sha256']
 assert mux['video_stream_sha256']==reference,'Current mux video packets differ from reviewed baseline.'
 return {'final_video_sha256':current,'audio':audio,'processing':processing,'baseline':baseline,'locked_video':{'file':baseline['locked_silent_file'],'sha256':baseline['locked_silent_sha256'],'video_stream_sha256':reference,'duration_seconds':315,'frames':9450,'fps':30,'width':1920,'height':1080}}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--final',action='store_true');args=ap.parse_args()
 try:ready=final_ready()
 except(AssertionError,KeyError,FileNotFoundError)as e:
  print(json.dumps({'status':'WAITING_FOR_FINAL_VALIDATION','production_complete':False,'archive_written':False,'reason':str(e)},ensure_ascii=False));return 2
 if not args.final:print(json.dumps({'status':'READY_FOR_EXPLICIT_FINAL_PACKAGING','archive_written':False}));return 0
 paths=[];payloads={};rows=[];redactions=[]
 for path in sorted(ROOT.rglob('*')):
  rel=path.relative_to(ROOT)
  if any(x in {'node_modules','__pycache__','.DS_Store'}or x.startswith('.')for x in rel.parts):continue
  assert not path.is_symlink(),'Source symlink: '+str(rel)
  if path.is_file():paths.append((SOURCE_PREFIX+rel.as_posix(),path,'source'))
 for path in sorted(OUT.rglob('*')):
  rel=path.relative_to(OUT)
  if any(x.startswith('.')or x.startswith('source-reproduction-attempt')for x in rel.parts):continue
  if path.is_file()and path.suffix in {'.json','.md'}and path.name not in EXCLUDED_RECEIPTS:paths.append(('out/showcase-v11/'+rel.as_posix(),path,'scoped_evidence'))
 for name,path,kind in paths:
  raw=path.read_bytes();data,fields=sanitized_export(name,raw);assert not signed_hits(name,data),'Signed URL remains in '+name
  if fields:redactions.append({'file':name,'original_sha256':sha(raw),'packaged_sha256':sha(data),'removed_fields':fields})
  payloads[name]=data;rows.append({'file':name,'sha256':sha(data),'bytes':len(data),'kind':kind})
 for name,h in bindings(ready['processing']).items():assert relative(name)and sha(payloads[SOURCE_PREFIX+name])==h,'Export changes active input: '+name
 ident=source_identity(rows);prior=OUT/'source-reproduction-validation.json'
 if prior.is_file()and load(prior).get('status')=='SOURCE_PASS':assert load(prior)['immutable_source_identity']==ident,'Execution source changed after fresh reproduction.'
 manifest={'revision':11,'production_complete':True,'delivery_status':'FINAL','human_acceptance':'PENDING_USER_REVIEW','duration_seconds':315,'frames':9450,'speech_tempo':1,'pitch_cents':0,'new_speech_generation':False,'voice_processing':'single_constant_gain_only','final_video_sha256':ready['final_video_sha256'],'locked_video':ready['locked_video'],'snapshot':{'directory':'visual-source-v10','files':172,'baseline_revision':10,'baseline_provenance_file':'baseline-provenance.json','baseline_provenance_sha256':file_sha(ROOT/'baseline-provenance.json'),'prior_audio_and_visual_builders_are_historical':True},'active_audio':{'processing_manifest':'audio-processing-manifest.json','processing_manifest_sha256':sha(payloads[SOURCE_PREFIX+'audio-processing-manifest.json']),'source_identity_sha256':ready['processing']['source_identity_sha256']},'immutable_source_identity':ident,'signed_generation_urls_omitted':True,'export_redactions':redactions,'files':rows}
 target=OUT/ARCHIVE_NAME;temporary=target.with_suffix('.partial.zip')
 with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for name,data in payloads.items():z.writestr(name,data)
  z.writestr('SOURCE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 with zipfile.ZipFile(temporary)as z:assert z.testzip()is None,'ZIP CRC failure.'
 temporary.replace(target);print(json.dumps({'status':'PACKAGED_FINAL','file':str(target),'bytes':target.stat().st_size,'sha256':file_sha(target),'files':len(rows),'immutable_source_identity':ident,'redacted_files':len(redactions)}));return 0
if __name__=='__main__':raise SystemExit(main())
