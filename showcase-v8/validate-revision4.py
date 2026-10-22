#!/usr/bin/env python3
"""Independent Revision 4 validation. Old validation reports are never reused.

--source-only checks source, native layouts, and the new PCM/timing evidence.
Complete validation also checks the rendered and muxed final MP4.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import wave
HERE=Path(__file__).resolve().parent
EXPECTED_V3_SHA='0ecb12ca627bb1ffb2a5cce0ec13cc864f71e8ac235f978ee947959ef2fb1de4'
ANCHORS=['spec.json','timeline.json','stage.mjs','hero-scenes.js','task-scenes.js','narration/ko.json','narration/speech-edit-map.json','narration/revision-manifest.json']
HISTORICAL_URL_JSON={'narration/receipt.json','narration/generation-result.json','narration/fast-receipt.json','narration/fast-generation-failure.json'}
EXPECTED_SECTIONS=['opening','task3','task4','task5','task7','task8','task9','task11','task12','task13','task14','task17','task16','ending']
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def run(a,timeout=180):return subprocess.run(a,check=True,capture_output=True,text=True,timeout=timeout)
def pcm(p):
 with wave.open(str(p)) as w:
  assert (w.getframerate(),w.getnchannels(),w.getsampwidth())==(48000,1,2),str(p)
  return w.readframes(w.getnframes())
def norm(s):return ''.join(str(s).split())
def packaged_redaction_matches(f,old,actual,mapping,portable):
 r=mapping.get(f,{})
 return portable and f in HISTORICAL_URL_JSON and r.get('original_sha256')==old and r.get('packaged_sha256')==actual and bool(r.get('removed_fields'))

NATIVE_JS=r"""
import fs from 'node:fs';import path from 'node:path';import {createRequire} from 'node:module';import {createHash} from 'node:crypto';
const root=process.cwd(),base=process.env.LAYOUT_BASELINE,require=createRequire(path.join(root,'package.json'));let native;
try{native=require('@napi-rs/canvas')}catch{native=require('/Users/jk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@napi-rs/canvas')}
const {createCanvas,loadImage,GlobalFonts}=native;
const {drawFrame,taskHeaderContract}=await import(path.join(root,'stage.mjs')),{drawFrame:drawOld}=await import(path.join(base,'stage.mjs'));
const {heroSceneContract}=await import(path.join(root,'hero-scenes.js')),{taskSceneContract,getTaskPlacement}=await import(path.join(root,'task-scenes.js'));
const spec=JSON.parse(fs.readFileSync('spec.json')),oldspec=JSON.parse(fs.readFileSync(path.join(base,'spec.json'))),timeline=JSON.parse(fs.readFileSync('timeline.json'));
GlobalFonts.registerFromPath(path.join(root,'fonts/NotoSansCJKkr-Regular.otf'),'Noto');GlobalFonts.registerFromPath(path.join(root,'fonts/NotoSansCJKkr-Bold.otf'),'Noto');
const assets={images:{},backgrounds:{},videos:{},microscopy:{},transitionCanvas:createCanvas(1920,1080),spec,tasks:spec.sections.filter(s=>s.type==='task'),drawTitles:false,drawCaptions:false},cache=new Map();
async function im(file){if(!cache.has(file))cache.set(file,await loadImage(path.join(root,file)));return cache.get(file)}
for(const file of new Set(spec.sections.map(s=>s.reference_image).filter(Boolean)))assets.images[file]=await im(file);
for(const s of spec.sections){assets.backgrounds[s.id]={};for(let i=0;i<s.cuts.length;i++){const f=s.backgrounds?.[i]||s.cuts[i].photo_crop||s.cuts[i].background||s.photo_crops?.[i];if(f){assets.backgrounds[s.id][i]=await im(f);assets.images[f]=assets.backgrounds[s.id][i]}}}
for(const[id,f]of Object.entries(spec.microscopy||{}))assets.microscopy[id]=await im(f);
for(let i=1;i<=9;i++)assets.images['opening'+i]=await im('assets/opening/cut'+String(i).padStart(2,'0')+'.png');
function instrument(){
 const canvas=createCanvas(1920,1080),ctx=canvas.getContext('2d');let calls={text:[],rect:[],bezel:[],images:[]};
 const box=(x,y,w,h)=>{const m=ctx.getTransform(),p=[[x,y],[x+w,y],[x,y+h],[x+w,y+h]].map(([a,b])=>[m.a*a+m.c*b+m.e,m.b*a+m.d*b+m.f]);return {left:Math.min(...p.map(v=>v[0])),right:Math.max(...p.map(v=>v[0])),top:Math.min(...p.map(v=>v[1])),bottom:Math.max(...p.map(v=>v[1]))}};
 const ft=ctx.fillText.bind(ctx);ctx.fillText=function(s,x,y,...rest){calls.text.push({text:String(s),font:ctx.font,alpha:ctx.globalAlpha,x,y,align:ctx.textAlign,advance_width:ctx.measureText(String(s)).width});return ft(s,x,y,...rest)};
 const rc=ctx.rect.bind(ctx);ctx.rect=function(x,y,w,h){calls.rect.push({local:[x,y,w,h],bounds:box(x,y,w,h)});return rc(x,y,w,h)};
 const rr=ctx.roundRect.bind(ctx);ctx.roundRect=function(x,y,w,h,...rest){if(x===-12&&y===-13&&w>1100&&h>560)calls.bezel.push(box(x,y,w,h));return rr(x,y,w,h,...rest)};
 const di=ctx.drawImage.bind(ctx);ctx.drawImage=function(image,...a){let d;if(a.length===4)d=a;else if(a.length===8)d=a.slice(4);if(d&&d[2]>=1800&&d[3]>=800)calls.images.push(box(...d));return di(image,...a)};
 return {canvas,ctx,reset(){calls={text:[],rect:[],bezel:[],images:[]}},get(){return calls}};
}
const now=instrument(),old=instrument(),records=[],H=1080,W=1920;
const hash=c=>createHash('sha256').update(c.data()).digest('hex');
function stripStats(data){let sum=0,sum2=0,n=0,nonblack=0;for(let y=865;y<H;y+=4)for(let x=0;x<W;x+=4){const j=(y*W+x)*4,r=data[j],g=data[j+1],b=data[j+2],l=(r+g+b)/3;sum+=l;sum2+=l*l;n++;if(Math.max(Math.abs(r-8),Math.abs(g-8),Math.abs(b-8))>3)nonblack++}return {samples:n,mean:sum/n,std:Math.sqrt(Math.max(0,sum2/n-(sum/n)**2)),nonblack_fraction:nonblack/n}}
// Native canvas exposes its affine matrix at float precision.
function sameBounds(a,b){return !!a&&['left','right','top','bottom'].every(k=>Math.abs(a[k]-b[k])<.0001)}
for(let i=0;i<timeline.entries.length;i++){
 const e=timeline.entries[i],section=spec.sections.find(s=>s.id===e.section_id),d=e.end-e.start;
 const local=Math.max(.01,d-Math.min(.06,d*.05)),t=e.start+local;
 now.reset();const state=drawFrame(now.ctx,t,timeline,spec,assets),calls=now.get(),one=hash(now.canvas),pixels=Buffer.from(now.canvas.data());
 now.reset();drawFrame(now.ctx,t,timeline,spec,assets);const deterministic=one===hash(now.canvas);
 old.reset();drawOld(old.ctx,t,timeline,oldspec,assets);const before=old.get(),oldHash=hash(old.canvas);
 const words=x=>x.text.filter(t=>t.alpha>.0001&&t.y>=154).map(t=>[t.text,t.font]);
 const hero=section.type!=='task',after=section.type==='task'&&e.kind!=='title'&&e.cut_index>0;
 let placement=null,bezelObserved=null;
 if(after){placement=getTaskPlacement(section,local);bezelObserved=calls.bezel.find(b=>sameBounds(b,placement.bezelBounds))||null}
 records.push({entry_index:i,section_id:e.section_id,kind:e.kind,cut_index:e.cut_index,cut_id:e.cut_id,time:t,local_seconds:local,captions:state.captions,task_header:state.task_header,text:calls.text,text_and_font_unchanged:JSON.stringify(words(calls))===JSON.stringify(words(before)),deterministic,pixel_sha256:one,pixels_same_as_v3:one===oldHash,body_pixels_unchanged:createHash('sha256').update(pixels.subarray(154*1920*4)).digest('hex')===createHash('sha256').update(old.canvas.data().subarray(154*1920*4)).digest('hex'),
 hero,hero_full_height_clip:hero?calls.rect.some(r=>r.local.join(',')==='0,0,1920,1080'):null,bottom_strip:hero?stripStats(pixels):null,baseline_bottom_strip:hero?stripStats(old.canvas.data()):null,large_photograph_bounds:hero?calls.images:undefined,after,placement,observed_bezel_bounds:bezelObserved,all_observed_bezel_bounds:after?calls.bezel:undefined,bezel_matches_actual_draw:after?!!bezelObserved:null});
}
const placements=[];
for(const section of spec.sections.filter(s=>s.type==='task'))for(const local of [0,.5,1,2,4,10])placements.push({section_id:section.id,local_seconds:local,...getTaskPlacement(section,local)});
console.log(JSON.stringify({hero_contract:heroSceneContract,task_contract:taskSceneContract,header_contract:taskHeaderContract,records,placements,scope:'Actual native draw calls, pixels and shared placement contract. Final encoded frames require separate visual review.'}));
"""

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path);p.add_argument('--out',type=Path,default=HERE.parent/'out/showcase-v4');p.add_argument('--video',type=Path);p.add_argument('--baseline-video',type=Path,default=HERE.parent/'out/showcase-v3/RD_Process_AI_Fast_Track_Showcase_Revision3.mp4');p.add_argument('--source-only',action='store_true');p.add_argument('--node',default='node');a=p.parse_args()
 out=a.out;out.mkdir(parents=True,exist_ok=True);baseline=a.baseline or (HERE.parent/'showcase-v3' if (HERE.parent/'showcase-v3/spec.json').exists() else HERE/'baseline-v3');video=a.video or out/'RD_Process_AI_Fast_Track_Showcase_Revision4.mp4';target=out/('revision4-source-validation.json' if a.source_only else 'revision4-validation.json')
 report={'status':'WAIT','scope':'Independent Revision 4 source, 87-entry native layout, slower continuous narration and final-media checks.','checks':[],'limitations':[]}
 def save():target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 def check(name,ok,**data):
  report['checks'].append({'check':name,'passed':bool(ok),**data})
  if not ok:print('FAIL '+name,flush=True)
 required=[HERE/'revision3-baseline-provenance.json',HERE/'spec.json',HERE/'timeline.json',HERE/'narration/speech-edit-map-v4.json',HERE/'narration/revision-manifest-v4.json',out/'narration-raw.wav',out/'audio.wav',out/'audio-validation.json',*[baseline/f for f in ANCHORS]]
 if not a.source_only:required += [video,out/'render-validation.json',out/'video_silent.mp4',out/'mux-validation.json',out/'visual-validation.json',out/'contact-sheet-manifest.json',out/'final-speech-review.json']
 missing=[str(f) for f in required if not f.exists()]
 if missing:report['missing']=missing;save();print(json.dumps({'status':'WAIT','missing':missing}));return 2
 try:
  provenance=read(HERE/'revision3-baseline-provenance.json');files={r['file']:r for r in provenance['files']};portable=not (baseline/'reference').exists();frozen={f:sha(HERE/f) for f in ['spec.json','timeline.json','stage.mjs','hero-scenes.js','task-scenes.js','render.mjs','narration/ko.json','narration/take.wav','narration/speech-edit-map-v4.json','narration/revision-manifest-v4.json','revision3-baseline-provenance.json']}
  checkfiles=ANCHORS if portable else list(files);bad=[f for f in checkfiles if not (baseline/f).exists() or sha(baseline/f)!=files[f]['sha256']]
  check('all_original_v3_source_files_unchanged',len(files)==212 and not bad,mode='portable eight-file baseline and immutable input hashes' if portable else 'complete 212-file original v3 source',mismatches=bad)
  immutable=[f for f in files if f.startswith(('reference/','assets/','fonts/','narration/'))];redactions=[];bad=[]
  for f in immutable:
   if not (HERE/f).exists():bad.append(f);continue
   actual=sha(HERE/f)
   if actual==files[f]['sha256']:continue
   if packaged_redaction_matches(f,files[f]['sha256'],actual,provenance.get('packaged_json_redactions',{}),portable):redactions.append({'file':f,**provenance['packaged_json_redactions'][f]})
   else:bad.append(f)
  report['historical_url_redactions']={'portable_mode':portable,'accepted':redactions,'scope':'Only four declared historical narration JSON URL redactions; no actual audio, image, script or workspace exceptions.'}
  check('original_md_assets_fonts_voice_and_ko_preserved',not bad and sum(f.startswith('reference/') and f.endswith('.md') for f in immutable)==20,checked_files=len(immutable),mismatches=bad)
  spec=read(HERE/'spec.json');old=read(baseline/'spec.json');expected=json.loads(json.dumps(old));expected['sections']=[s for s in expected['sections'] if s['type']!='summary'];next(c for s in expected['sections'] for c in s['cuts'] if c['id']=='task14_cut4')['title']='간편해진 업무 환경'
  check('only_four_summary_removals_and_cubic_after_title_change',spec==expected)
  check('four_summary_sections_completely_absent_and_task_order_fixed',[s['id'] for s in spec['sections']]==EXPECTED_SECTIONS and all(s['type']!='summary' for s in spec['sections']))
  check('opening_ending_and_scene_programs_unchanged',next(s for s in spec['sections'] if s['id']=='opening')==next(s for s in old['sections'] if s['id']=='opening') and next(s for s in spec['sections'] if s['id']=='ending')==next(s for s in old['sections'] if s['id']=='ending') and all(sha(HERE/f)==sha(baseline/f)==files[f]['sha256'] for f in ['hero-scenes.js','task-scenes.js','narration/ko.json']))
  tl=read(HERE/'timeline.json');oldtl=read(baseline/'timeline.json');entries=tl['entries'];original=[e for e in oldtl['entries'] if not e['section_id'].startswith('summary')];sig=lambda e:(e['section_id'],e['kind'],e.get('cut_index'),e.get('cut_id'),e.get('caption',''))
  check('eighty_seven_entry_order_and_seventy_three_original_narration_cuts',len(entries)==87 and sum(e['kind']=='cut' for e in entries)==73 and [sig(e) for e in entries]==[sig(e) for e in original] and not any(e['kind']=='summary' for e in entries))
  check('same_307_second_duration_and_9214_gapless_frames',tl['fps']==30 and tl['frames']==9214 and abs(tl['duration']-oldtl['duration'])<1e-8 and entries[0]['start_frame']==0 and entries[-1]['end_frame']==9214 and all(e['start_frame']<e['end_frame'] and abs(e['start']-e['start_frame']/30)<1e-7 and abs(e['end']-e['end_frame']/30)<1e-7 for e in entries) and all(x['end_frame']==y['start_frame'] for x,y in zip(entries,entries[1:])),duration=tl['duration'],frames=tl['frames'])
  oldcuts={e['cut_id']:e for e in original if e.get('cut_id')}
  check('narration_exposure_not_shortened_and_task_titles_remain_two_seconds',all(e['end_frame']-e['start_frame']>=oldcuts[e['cut_id']]['end_frame']-oldcuts[e['cut_id']]['start_frame'] for e in entries if e['kind']=='cut') and len([e for e in entries if e['kind']=='title'])==12 and all(e['end_frame']-e['start_frame']==60 for e in entries if e['kind']=='title') and entries[-1]['kind']=='silent' and entries[-1]['start_frame']==9094 and entries[-1]['end_frame']==9214)
  print('Checking 87 native compositions and 72 actual task headers',flush=True)
  native=json.loads(subprocess.run([a.node,'--input-type=module','-e',NATIVE_JS],cwd=HERE,env={**os.environ,'LAYOUT_BASELINE':str(baseline.resolve())},check=True,capture_output=True,text=True,timeout=180).stdout);(out/'native-revision4-validation.json').write_text(json.dumps(native,ensure_ascii=False,indent=2)+'\n');rows=native['records'];headers=[r for r in rows if r['section_id'].startswith('task')];heroes=[r for r in rows if r['hero']];tasks={s['id']:s for s in spec['sections'] if s['type']=='task'}
  check('all_87_native_frames_deterministic_and_no_narration_captions',len(rows)==87 and all(r['deterministic'] and r['captions']==[] for r in rows))
  check('existing_core_text_fonts_and_pixels_below_header_preserved',all(r['text_and_font_unchanged'] and r['body_pixels_unchanged'] for r in rows),failures=[r['entry_index']+1 for r in rows if not (r['text_and_font_unchanged'] and r['body_pixels_unchanged'])])
  header_fail=[]
  for r in headers:
   h=r.get('task_header');sec=tasks[r['section_id']]
   if not h:header_fail.append({'entry':r['entry_index']+1,'reason':'no header'});continue
   rs=h['records'];title=''.join(v['text'] for v in rs if v['role']=='task_title');owner=''.join(v['text'] for v in rs if v['role']=='owner');left=''.join(v['text'] for v in rs if v['role']=='cut_title')
   expected_cut=sec['cuts'][r['cut_index']]['title'] if r['kind']!='title' else ''
   if norm(title)!=norm(sec['title']) or owner!=sec['owner'] or norm(left)!=norm(expected_cut) or h['task_title']!=sec['title'] or h['owner']!=sec['owner']:header_fail.append({'entry':r['entry_index']+1,'reason':'header copy'})
   for v in rs:
    b=v['bounds'];isleft=v['role']=='cut_title';minx,maxx=(104,1042) if isleft else (1106,1816)
    if not (minx<=b['left']<b['right']<=maxx and 0<=b['top']<b['bottom']<=154):header_fail.append({'entry':r['entry_index']+1,'reason':'header bbox','role':v['role']})
    if not any(t['text']==v['text'] and t['font']==v['font'] and abs(t['x']-v['x'])<1e-6 and abs(t['y']-v['y'])<1e-6 and t['alpha']>.99 for t in r['text']):header_fail.append({'entry':r['entry_index']+1,'reason':'header not actually drawn','role':v['role']})
   leftbox=[v['bounds'] for v in rs if v['role']=='cut_title'];rightbox=[v['bounds'] for v in rs if v['role']!='cut_title']
   if leftbox and rightbox and max(b['right'] for b in leftbox)>=min(b['left'] for b in rightbox):header_fail.append({'entry':r['entry_index']+1,'reason':'left/right collision'})
  check('all_twelve_exact_names_and_owners_drawn_in_72_nonoverlapping_headers',len(headers)==72 and len({r['section_id'] for r in headers})==12 and not header_fail,headers=len(headers),failures=header_fail)
  hc=native['hero_contract'];check('fifteen_hero_scenes_keep_full_1080_height',len(heroes)==15 and hc['height']==1080 and hc['captionReservedHeight']==0 and all(r['hero_full_height_clip'] and r['bottom_strip']['nonblack_fraction']>.01 and r['bottom_strip']['std']>.35 for r in heroes))
  after=[r for r in rows if r['after']];check('forty_eight_after_monitors_keep_full_height_geometry',len(after)==48 and all(r['bezel_matches_actual_draw'] for r in after) and all(v['bezelBounds']['top']>=154 and v['bezelBounds']['bottom']<=1080 for v in native['placements']))
  cubic=[r for r in rows if r['section_id']=='task14'];check('cubic_before_after_title_annotations_absent',all(not any(tag in t['text'] for tag in ['(Before)','(After)']) for r in cubic for t in r['text']))
  final=next(r for r in rows if r['section_id']=='ending' and r['cut_index']==5);words=[t['text'] for t in final['text']];check('award_team_and_owner_labels_preserved',all(t in words for t in ['N-PMA','김지은 TL','DRAM트랙Photo','장민희 TL']))
  print('Checking slower continuous narration PCM and all mapped phrase tails',flush=True)
  speech=read(HERE/'narration/speech-edit-map-v4.json');m=read(HERE/'narration/revision-manifest-v4.json');previous=read(baseline/'narration/speech-edit-map.json');conf=read(HERE/'narration/ko.json');info=m['processed_master'];path=HERE/info['path'];processed=pcm(path);raw=pcm(out/'narration-raw.wav');rate=m['tempo_ratio'];duration=len(processed)/96000;prevdur=previous['processed_continuous']['sample_count']/48000
  check('same_original_take_voice_model_script_and_single_processing_pass',speech['source_master']['sha256']==sha(HERE/'narration/take.wav')==files['narration/take.wav']['sha256'] and speech['source_config_sha256']==sha(HERE/'narration/ko.json') and speech['new_tts'] is False and speech['script_unchanged'] is True and all(speech[k]==conf[k] for k in ['voice_id','voice_name','model_id']) and info['continuous_processing_passes']==1 and speech['processed_continuous']['continuous_processing_passes']==1)
  check('narration_extended_exactly_24_seconds_at_approved_slower_pace',abs(duration-prevdur-24)<=1/48000 and abs(rate-1.1348118)<.0002 and rate==speech['tempo_ratio']==tl['tempo'] and rate<m['previous_tempo_ratio'] and m['previous_tempo_ratio']==oldtl['tempo'],previous_voice_seconds=prevdur,new_voice_seconds=duration,voice_extension_seconds=duration-prevdur,tempo_setting=rate,duration_based_speed_ratio=prevdur/duration)
  check('new_processed_master_file_and_pcm_hashes_match',sha(path)==info['sha256']==speech['processed_continuous']['sha256'] and hashlib.sha256(processed).hexdigest()==info['pcm_sha256']==speech['processed_continuous']['pcm_sha256'] and len(processed)//2==info['sample_count'])
  bad=[];lastsrc=0;lastdst=0;parts=[]
  for i,pl in enumerate(m['placements']):
   x,y,d,n=pl['source_start_sample'],pl['source_end_sample'],pl['timeline_start_sample'],pl['sample_count']
   if x!=lastsrc or y-x!=n or d<lastdst or raw[d*2:(d+n)*2]!=processed[x*2:y*2] or any(raw[lastdst*2:d*2]):bad.append(i)
   parts.append(raw[d*2:(d+n)*2]);lastsrc=y;lastdst=d+n
  check('all_new_processed_pcm_placed_once_in_order_with_only_inserted_silence',len(m['placements'])==23 and not bad and b''.join(parts)==processed and not any(raw[lastdst*2:]),failures=bad,placements=len(m['placements']))
  cs={c['cut_id']:c for c in speech['cuts']};declared={c['cut_id']:c for c in m['per_cut_timing']};timing=[];bad=[]
  for e in [e for e in entries if e['kind']=='cut']:
   c=cs[e['cut_id']];end=c['actual_speech_end_sample'];ps=[pl for pl in m['placements'] if pl['section_id']==e['section_id'] and pl['source_start_sample']<=end<=pl['source_end_sample'] and pl.get('cut_id') in [None,e['cut_id']]]
   if len(ps)!=1:bad.append(e['cut_id']);continue
   pl=ps[0];actual=pl['timeline_start_sample']+end-pl['source_start_sample'];margin=e['end']-actual/48000
   if actual!=declared[e['cut_id']]['actual_speech_end_sample'] or abs(declared[e['cut_id']]['visual_end_seconds']-e['end'])>1e-7 or margin<0 or c['safe_boundary_sample']<end or c['caption']!=e['caption']:bad.append(e['cut_id'])
   timing.append({'cut_id':e['cut_id'],'actual_speech_end_seconds':actual/48000,'transition_seconds':e['end'],'margin_seconds':margin,'confidence':c['confidence']})
  check('all_73_original_caption_tails_finish_before_visual_transition',len(timing)==73 and not bad,failures=bad,minimum_margin_seconds=min(r['margin_seconds'] for r in timing));report['per_cut_timing']=timing
  timing_by_id={r['cut_id']:r for r in timing};task_tails=[timing_by_id[e['cut_id']]['margin_seconds'] for e in entries if e['section_id'].startswith('task') and e['kind']=='cut' and e['cut_index']==4]
  check('all_twelve_task_final_tails_finish_at_least_200ms_before_next_scene',len(task_tails)==12 and min(task_tails)>=.2,minimum_task_tail_seconds=min(task_tails))
  silent=[e for e in entries if e['kind'] in ['title','summary','silent']];bad=[e['section_id'] for e in silent if any(raw[e['start_frame']*1600*2:e['end_frame']*1600*2])];check('fourteen_silent_entries_have_exact_zero_raw_narration',len(silent)==14 and not bad,failures=bad)
  sectbad=[];joined=[]
  for sec in speech['sections']:
   part=HERE/'narration/retimed-sections-v4'/Path(sec['pcm_file']).name
   if not part.exists():part=HERE/sec['pcm_file'] if not Path(sec['pcm_file']).is_absolute() else Path(sec['pcm_file'])
   content=pcm(part);joined.append(content)
   if sha(part)!=sec['file_sha256'] or hashlib.sha256(content).hexdigest()!=sec['pcm_sha256']:sectbad.append(sec['section_id'])
  check('fourteen_saved_voice_sections_reassemble_complete_processed_pcm',len(joined)==14 and not sectbad and b''.join(joined)==processed,failures=sectbad)
  report['speech_boundary_caveats']=[{'cut_id':c['cut_id'],'confidence':c['confidence'],'continuous_start_overlap':c.get('continuous_start_overlap',False),'character_coverage':c.get('character_coverage')} for c in speech['cuts'] if c.get('confidence')=='REVIEWED_CONTINUOUS_SPEECH_VISUAL_ONLY' or c.get('continuous_start_overlap') or c.get('character_coverage',1)<.9]
  audio=read(out/'audio-validation.json');check('new_audio_mix_hash_and_existing_bgm_preserved',audio['status']=='PASS' and audio['audio_sha256']==sha(out/'audio.wav') and audio['original_master_sha256']==sha(HERE/'narration/take.wav') and audio['tempo_ratio']==rate and audio['voice_extension_seconds']==24 and audio['bgm_source_sha256']==sha(HERE/conf['bgm']) and audio['bgm_gain']==.2 and audio['bgm_crossfade_seconds']==3 and audio['bgm_fade_in_seconds']==1 and audio['bgm_fade_out_seconds']==1.5)
  if not a.source_only:
   print('Checking newly encoded final MP4 and current render hashes',flush=True)
   meta=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]).stdout);vs=[s for s in meta['streams'] if s['codec_type']=='video'];ads=[s for s in meta['streams'] if s['codec_type']=='audio'];subs=[s for s in meta['streams'] if s['codec_type']=='subtitle']
   check('final_1080p_30fps_9214_frames_stereo_48k_aac_without_subtitles',len(vs)==len(ads)==1 and not subs and vs[0]['width']==1920 and vs[0]['height']==1080 and vs[0]['r_frame_rate']=='30/1' and int(vs[0]['nb_frames'])==9214 and ads[0]['codec_name']=='aac' and ads[0]['channels']==2 and int(ads[0]['sample_rate'])==48000 and abs(float(meta['format']['duration'])-tl['duration'])<1/30)
   packet_hash=lambda f:run(['ffmpeg','-v','error','-i',str(f),'-map','0:v:0','-c:v','copy','-f','hash','-hash','sha256','-']).stdout.strip()
   check('new_native_video_stream_copied_exactly',packet_hash(video)==packet_hash(out/'video_silent.mp4'))
   render=read(out/'render-validation.json');check('native_render_hashes_current',render['status']=='PASS' and render['sha256']==sha(out/'video_silent.mp4') and all(sha(HERE/r['file'])==r['sha256'] for r in render['inputs']))
   mux=read(out/'mux-validation.json');check('new_pcm_to_aac_mux_provenance',mux['status']=='PASS' and mux['final_sha256']==sha(video) and mux['audio_pcm_sha256']==sha(out/'audio.wav') and mux['audio_reencoded'] is True and mux['new_tts'] is False and mux['video_stream_copied'] is True)
   visual=read(out/'visual-validation.json');check('all_87_current_native_stills_and_active_motion',len(visual['records'])==87 and all(r['caption']==[] for r in visual['records']) and len(visual['motion'])==75 and all(r['moving'] for r in visual['motion']))
   contact=read(out/'contact-sheet-manifest.json');stills={r['file'] for r in visual['records']};bad=[]
   for r in contact['records']:
    file=Path(r['file']);file=file if file.exists() else out/'stills'/file.name
    if not file.exists() or sha(file)!=r['sha256'] or file.name not in stills:bad.append(str(file))
   check('contact_sheets_cover_all_87_current_stills',len(contact['records'])==87 and not bad and all(sha(HERE/f)==h for f,h in contact['source_hashes'].items()),failures=bad)
   review=read(out/'final-speech-review.json');review_hashes=review.get('source_hashes',{})
   check('fresh_final_speech_review_passes_with_variants_explicit',review['status'] in ['PASS','PASS_WITH_ASR_VARIANTS'] and all(review['checks'].values()) and len(review_hashes)==8 and all((HERE.parent/f).exists() and sha(HERE.parent/f)==h for f,h in review_hashes.items()),status=review['status']);report['speech_review_status']=review['status']
   run(['ffmpeg','-v','error','-i',str(video),'-f','null','-']);check('complete_final_video_and_aac_decode',True)
   if a.baseline_video.exists():check('original_v3_final_preserved',sha(a.baseline_video)==EXPECTED_V3_SHA)
   report.update({'video':str(video),'file_sha256':sha(video),'duration_seconds':float(meta['format']['duration']),'frames':9214})
  check('validation_inputs_unchanged',all(sha(HERE/f)==h for f,h in frozen.items()))
  report['limitations'].append('Native geometry and PCM checks are separate from visual contact-sheet/encoded-frame review and continuous playback. Existing local ASR variants and reviewed continuous-speech visual boundaries remain explicit; no new voice is generated.')
  report['status']=('SOURCE_PASS' if a.source_only else 'PASS') if all(c['passed'] for c in report['checks']) else 'FAIL'
 except Exception as exc:report.update({'status':'FAIL','failure':str(type(exc).__name__)+': '+str(exc)})
 save();print(json.dumps({'status':report['status'],'report':str(target),'checks':len(report['checks']),'passed':sum(c['passed'] for c in report['checks']),'failure':report.get('failure')},ensure_ascii=False));return 0 if report['status'] in ['PASS','SOURCE_PASS'] else 1
if __name__=='__main__':sys.exit(main())
