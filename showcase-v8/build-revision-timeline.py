#!/usr/bin/env python3
"""Place complete existing speech at its saved pace; revise visual timing only."""
from pathlib import Path
import hashlib,json,math,wave
HERE=Path(__file__).resolve().parent
BASE=HERE/'baseline'
FPS=30;SR=48000;SPF=SR//FPS
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def frames(samples):return math.ceil(samples/SPF-1e-9)
def main():
 old=read(BASE/'timeline.json');spec=read(HERE/'spec.json');mapping=read(HERE/'narration/speech-edit-map.json')
 assert mapping['sample_rate']==SR
 assert abs(mapping['tempo_ratio']-old['tempo'])<1e-12
 sections={s['section_id']:s for s in mapping['sections']}
 cuts={c['cut_id']:c for c in mapping['cuts']}
 assert len(cuts)==73 and len(sections)==14
 entries=[];placements=[];section_records=[];cursor=0
 def add(original,endframe):
  nonlocal cursor
  assert endframe>cursor,(original['section_id'],original.get('cut_id'),cursor,endframe)
  e={**original,'start_frame':cursor,'end_frame':endframe,'start':cursor/FPS,'end':endframe/FPS}
  for k in ['source_start','source_end','source_start_sample','source_end_sample']:
   if k in e:e['baseline_'+k]=e.pop(k)
  if e.get('cut_id'):
   c=cuts[e['cut_id']]
   e['processed_source_start_sample']=c['processed_start_sample'];e['processed_source_end_sample']=c['processed_end_sample']
  entries.append(e);cursor=endframe;return e
 def place(sid,a,b,dest,cut_id=None):
  assert b>a
  placements.append({'section_id':sid,'cut_id':cut_id,'source_start_sample':a,'source_end_sample':b,'timeline_start_sample':dest,'sample_count':b-a})
 for sec in spec['sections']:
  sid=sec['id'];original=[e for e in old['entries'] if e['section_id']==sid]
  section_begin=cursor
  if sec['type']=='summary':
   add(original[0],cursor+original[0]['end_frame']-original[0]['start_frame']);continue
  info=sections[sid];a=info['start_sample'];b=info['end_sample']
  if sec['type']=='task':add(original[0],cursor+60)
  body_start=cursor;voice_entries=[e for e in original if e['kind']=='cut']
  if sec['type']=='opening':
   target=old['entries'][8]['end_frame']+135
   bounds=[a]+[cuts[e['cut_id']]['safe_boundary_sample'] for e in voice_entries[:-1]]+[b]
   baseframes=[frames(y-x) for x,y in zip(bounds,bounds[1:])]
   extra=target-sum(baseframes)
   assert extra>=90,('Opening speech unexpectedly exceeds the requested exposure time',extra)
   weights=[.55,.50,.30,.30,.65,.60,.50,.45,.65]
   allocations=[int(extra*w/sum(weights)) for w in weights]
   remainder=extra-sum(allocations)
   ranking=sorted(range(9),key=lambda i:extra*weights[i]/sum(weights)-allocations[i],reverse=True)
   for i in ranking[:remainder]:allocations[i]+=1
   for e,x,y,base,pad in zip(voice_entries,bounds,bounds[1:],baseframes,allocations):
    place(sid,x,y,cursor*SPF,e['cut_id']);add(e,cursor+base+pad)
   assert cursor==target
  elif sec['type']=='task':
   place(sid,a,b,body_start*SPF)
   for i,e in enumerate(voice_entries):
    c=cuts[e['cut_id']]
    relative=c['safe_boundary_sample']-a
    if i==len(voice_entries)-1:
     relative=max(b-a,info['actual_speech_end_sample']-a+round(.20*SR))
    add(e,body_start+frames(relative))
  else:
   # Preserve the separate one-second ending transition and four-second card.
   split=cuts['ending_cut3']['safe_boundary_sample'];place(sid,a,split,body_start*SPF)
   cumulative_silent=0
   for e in original:
    if e['kind']=='silent':
     silent_frames=e['end_frame']-e['start_frame'];add(e,cursor+silent_frames)
     if e.get('cut_index')==3:
      cumulative_silent+=silent_frames
      place(sid,split,b,cursor*SPF)
     continue
    c=cuts[e['cut_id']];relative=c['safe_boundary_sample']-a
    if e['cut_id']=='ending_cut5':relative=max(b-a,info['actual_speech_end_sample']-a+round(.20*SR))
    add(e,body_start+frames(relative)+cumulative_silent)
  section_records.append({'section_id':sid,'source_start_sample':a,'source_end_sample':b,'timeline_start_sample':body_start*SPF,'timeline_end_sample':cursor*SPF,'visual_section_start_frame':section_begin,'visual_section_end_frame':cursor})
 def convert(sample,sid):
  rows=[p for p in placements if p['section_id']==sid and p['source_start_sample']<=sample<=p['source_end_sample']]
  assert rows,(sample,sid)
  p=rows[-1];return p['timeline_start_sample']+sample-p['source_start_sample']
 timing=[]
 for e in entries:
  if not e.get('cut_id'):continue
  c=cuts[e['cut_id']];start=convert(c['actual_speech_start_sample'],e['section_id']);end=convert(c['actual_speech_end_sample'],e['section_id'])
  first_visual=next(x for x in entries if x['section_id']==e['section_id'] and x['kind']=='cut')
  if e is first_visual:assert start>=e['start_frame']*SPF-2,(e['cut_id'],'paragraph begins before its task video',start,e['start_frame']*SPF)
  assert end<=e['end_frame']*SPF,(e['cut_id'],'speech exceeds its visual cut',end,e['end_frame']*SPF)
  timing.append({'cut_id':e['cut_id'],'section_id':e['section_id'],'actual_speech_start_sample':start,'actual_speech_end_sample':end,'visual_start_seconds':e['start'],'visual_end_seconds':e['end'],'tail_margin_seconds':(e['end_frame']*SPF-end)/SR,'speech_start_before_visual_seconds':max(0,(e['start_frame']*SPF-start)/SR),'boundary_confidence':c.get('confidence')})
 for s in section_records:
  info=sections[s['section_id']];s['last_speech_end_sample']=convert(info['actual_speech_end_sample'],s['section_id'])
 pcm_master={**mapping['processed_continuous']};master_path=HERE/'narration/processed-continuous.wav';assert sha(master_path)==pcm_master['sha256'];pcm_master['path']='narration/processed-continuous.wav';total=cursor/FPS
 result={**old,'duration':total,'duration_seconds':total,'frames':cursor,'max_seconds':None,'allow_over_five_minutes':True,'entries':entries,'audio_segments':placements,'sections':section_records,'revision':{'opening_extra_seconds':4.5,'narration_speed_unchanged':True,'narration_captions':False,'user_allowed_over_five_minutes':True}}
 manifest={'generation_mode':'single_take','source_master':read(HERE/'narration/manifest.json')['master'],'processed_master':pcm_master,'tempo_ratio':mapping['tempo_ratio'],'sample_rate':SR,'placements':placements,'sections':section_records,'per_cut_timing':timing,'speech_edit_map_sha256':sha(HERE/'narration/speech-edit-map.json'),'frames':cursor,'duration':total,'notes':['Speech PCM is placed directly from the continuous processed take. No new TTS or additional speed change is applied.','Opening exposure is exactly 4.5 seconds longer; silence is inserted between complete existing sentences.','Task titles and summaries retain their original durations and all chapter boundaries follow complete phonemes.']}
 (HERE/'timeline.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 (HERE/'narration/revision-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'duration':total,'frames':cursor,'opening_seconds':entries[8]['end'],'entries':len(entries),'speech_cuts':len(timing),'pcm_placements':len(placements),'minimum_tail_margin':min(c['tail_margin_seconds'] for c in timing)},ensure_ascii=False))
if __name__=='__main__':main()
