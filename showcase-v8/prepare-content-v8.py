#!/usr/bin/env python3
"""Apply the user's twelve-task revision to the accepted Revision6 sources."""
from pathlib import Path
import copy,hashlib,json,math
ROOT=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def main():
 draft=load(ROOT/'revision8-content.json');brief=load(ROOT/'reference/user-revision8-brief.json')
 baseline=load(ROOT/'baseline-v6/spec.json');old=load(ROOT/'baseline-v6/timeline.json')
 previous={s['id']:s for s in baseline['sections']};order=brief['order'];spec=copy.deepcopy(baseline)
 sections=[copy.deepcopy(previous['opening'])]
 for sid in order:
  latest=draft['tasks'][sid];s=copy.deepcopy(previous[sid])
  for key in ['title','team','owner']:s[key]=latest[key]
  s['revision8_user_content']=copy.deepcopy(brief['tasks'][sid])
  for i,(cut,latest_cut) in enumerate(zip(s['cuts'],latest['cuts'])):
   cut.update(title=latest_cut['title'],scene_title=latest_cut['title'],caption=latest_cut['narration'],narration=latest_cut['narration'],spoken_text=latest_cut['spoken_text'],screen_lines=latest_cut.get('key_phrases',[]),support_lines=latest_cut.get('key_phrases',[]),revision8_content=copy.deepcopy(latest_cut))
  sections.append(s)
 sections.append(copy.deepcopy(previous['ending']));spec['sections']=sections
 spec['output']['filename']='out/showcase-v8/RD_Process_AI_Fast_Track_Showcase_Revision8.mp4'
 spec['output']['max_seconds']=900
 spec['output']['timing_status']='Updated task narration determines cut lengths; approved opening/ending exposures remain exact.'
 spec['revision8']={'baseline_revision':6,'excluded_revision7_motion':True,'task_order':order,'brief':'reference/user-revision8-brief.json','brief_sha256':hashlib.sha256((ROOT/'reference/user-revision8-brief.json').read_bytes()).hexdigest(),'claims_policy':'User-supplied figures are attributed to the supplied material; candidate results, validation status and future plans stay explicit.'}
 save(ROOT/'spec.json',spec)
 conf=load(ROOT/'narration/ko.json');outer={b['section_id']:b for b in conf['blocks'] if b['section_id'] in ['opening','ending']}
 blocks=[]
 for sid in order:
  cuts=[{'id':f'{sid}_cut{i+1}','text':c['narration'],'spoken_text':c['spoken_text']}for i,c in enumerate(draft['tasks'][sid]['cuts'])]
  blocks.append({'section_id':sid,'cuts':cuts,'text':' '.join(c['text']for c in cuts),'spoken_text':' '.join(c['spoken_text']for c in cuts)})
 prompt=conf['delivery_tag']+'\n\n'+'\n\n[pause]\n\n'.join('\n\n'.join(c['spoken_text']for c in b['cuts'])for b in blocks)
 if conf.get('language_code')=='ko':prompt=prompt.replace('이미지 기반 오계측 후보 탐지와 대시보드 자연어 분석을 제공합니다.','이미지 기반 오계측 후보 탐지와, 대시보드 자연어 분석을 제공합니다.')
 conf.update(blocks=[outer['opening'],*blocks,outer['ending']],generation_mode='single_take',generation_scope='Twelve revised task blocks in one continuous take; approved opening and ending audio are reused.',generated_prompt=prompt)
 conf['pronunciation_map'].update({'K-param':'케이 파라미터','HyDisk':'하이디스크','Cube':'큐브','22개':'스물두개','122시간':'백이십이시간','1200초':'천이백초','1,200초':'천이백초','75초':'칠십오초','317건':'삼백십칠건','19건':'십구건','15분':'십오분','1시간':'한시간','5분':'오분','6초':'육초','0분':'영분','70%':'칠십퍼센트','80%':'팔십퍼센트','90%':'구십퍼센트','40%':'사십퍼센트','70퍼센트':'칠십퍼센트','80퍼센트':'팔십퍼센트','90퍼센트':'구십퍼센트','40퍼센트':'사십퍼센트'})
 save(ROOT/'narration/ko.json',conf);taskconf={**conf,'blocks':blocks};save(ROOT/'narration/tasks-ko.json',taskconf)
 (ROOT/'narration/full-script.txt').write_text('\n\n'.join(b['text']for b in conf['blocks'])+'\n')
 (ROOT/'narration/tasks-prompt.txt').write_text(prompt+'\n')
 # Preview only. The completed take replaces every estimate before final render.
 entries=[];cursor=0
 def add(e,count):
  nonlocal cursor
  row={**copy.deepcopy(e),'start_frame':cursor,'end_frame':cursor+count,'start':cursor/30,'end':(cursor+count)/30};entries.append(row);cursor+=count
 for e in old['entries']:
  if e['section_id']=='opening':add(e,e['end_frame']-e['start_frame'])
 for sid in order:
  original=[e for e in old['entries']if e['section_id']==sid];add(next(e for e in original if e['kind']=='title'),60)
  for i,c in enumerate(draft['tasks'][sid]['cuts']):
   e=next(e for e in original if e.get('cut_index')==i and e['kind']=='cut');e={**e,'caption':c['narration']};add(e,max(90,math.ceil((len(c['spoken_text'])/7.5+.35)*30)))
 for e in old['entries']:
  if e['section_id']=='ending':add(e,e['end_frame']-e['start_frame'])
 save(ROOT/'timeline-preview.json',{**old,'duration':cursor/30,'duration_seconds':cursor/30,'frames':cursor,'entries':entries,'allow_over_five_minutes':True,'preview_only':True,'timing_basis':'Estimated for layout review only. Actual word-safe narration timing must replace this before final output.'})
 print(json.dumps({'tasks':len(blocks),'spoken_cuts':sum(len(b['cuts'])for b in blocks),'prompt_characters':len(prompt),'preview_seconds':cursor/30,'order':order},ensure_ascii=False))
if __name__=='__main__':main()
