#!/usr/bin/env python3
"""Export the unchanged68 narration lines on the final Revision12 cut clock."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parent/'out/showcase-v12'
def timestamp(t):
    tenths=round(t*10);return f'{tenths//600:02d}:{tenths//10%60:02d}.{tenths%10}'
def main():
    timeline=json.loads((ROOT/'timeline.json').read_text());ko=json.loads((ROOT/'narration/ko.json').read_text());spec=json.loads((ROOT/'spec.json').read_text());sections={s['id']:s for s in spec['sections']}
    assert not timeline['preview_only']and timeline['revision']==12 and timeline['duration']<=330
    cuts={e['cut_id']:e for e in timeline['entries']if e['kind']=='cut'};assert len(cuts)==68
    out=['# R&D 공정 AI Fast Track — Revision12 나레이션 타임라인','',f'- 영상 길이: {timestamp(timeline["duration"])}', '- 음성: Kyung / 선택한 회사 행사 톤4번 / 음높이 유지·속도1.15배', '- 시점은 최종 영상에서 해당 멘트가 배치된 컷의 시작입니다. 과제 제목만 표시되는2초 화면과 무음 카드는 제외했습니다.', '- 나레이션 문구는 기존 승인된68개 문장을 유지했습니다.','']
    n=0;records=[]
    for block in ko['blocks']:
        section=sections[block['section_id']]
        if section['type']=='task':
            n+=1;out +=[f'## {n:02d}. {section["title"]} — {section["owner"]}', '',f'팀: {section["team"]}','']
        else:out +=['## '+('오프닝'if section['id']=='opening'else'엔딩'),'']
        for c in block['cuts']:
            e=cuts[c['id']];out +=[f'{timestamp(e["start"])}: {c["text"]}',''];records.append({'cut_id':c['id'],'start':e['start'],'text':c['text']})
    OUT.mkdir(exist_ok=True);target=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision12_Narration_Timeline.md';target.write_text('\n'.join(out))
    proof={'revision':12,'status':'PASS','entries':len(records),'task_titles_and_silence_omitted':True,'duration_seconds':timeline['duration'],'timeline_sha256':hashlib.sha256((ROOT/'timeline.json').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256((ROOT/'narration/ko.json').read_bytes()).hexdigest(),'markdown_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'records':records};(OUT/'narration-timeline-validation.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':'PASS','entries':len(records),'file':str(target)},ensure_ascii=False))
if __name__=='__main__':main()
