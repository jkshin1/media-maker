#!/usr/bin/env python3
"""Export the approved wording at actual placed speech starts."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'out/showcase-v10'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    timeline=json.loads((ROOT/'timeline.json').read_text())
    placement=json.loads((ROOT/'narration/placement-manifest.json').read_text())
    narration=json.loads((ROOT/'narration/ko.json').read_text())
    spec=json.loads((ROOT/'spec.json').read_text())
    captions={c['id']:c['text'] for b in narration['blocks'] for c in b['cuts']}
    speech={c['cut_id']:c for c in placement['cuts']}
    sections={s['id']:s for s in spec['sections']}
    def stamp(seconds):
        tenths=round(seconds*10)
        return f'{tenths//600:02d}:{tenths%600/10:04.1f}'
    rows=['# R&D 공정 AI Fast Track — 나레이션 타임라인','',
        '기준 영상: Revision10 / 전체 길이 05:15.0','',
        '형식: 나레이션 시점: 나레이션 내용',
        '시점은 최종 타임라인의 실제 발화 시작을 분:초.소수 첫째 자리로 표시했습니다. 나레이션이 없는 최종 카드는 제외했습니다.',
        'Lot의 화면 표기는 유지하며, 음성 원고에서는 ‘랏’으로 읽습니다. 68개 멘트의 문구와 읽는 속도를 유지했습니다.','']
    section_id=None;task=0;count=0
    for e in timeline['entries']:
        if e['cut_id']not in speech:continue
        if e['section_id']!=section_id:
            section_id=e['section_id'];s=sections[section_id]
            if section_id=='opening':heading='오프닝'
            elif section_id=='ending':heading='엔딩'
            else:task+=1;heading=f"{task:02d}. {s['title']} — {s['owner']}"
            rows.extend([f'## {heading}',''])
            if s.get('team'):rows.extend([f"팀: {s['team']}",''])
        text=captions[e['cut_id']]
        assert text==e['caption']
        rows.extend([f"{stamp(speech[e['cut_id']]['speech_start_seconds'])}: {text}",''])
        count+=1
    assert count==68 and task==12
    OUT.mkdir(parents=True,exist_ok=True)
    output=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision10_Narration_Timeline.md'
    output.write_text('\n'.join(rows))
    receipt={'status':'PASS','revision':10,'spoken_entries':count,'task_sections':task,'duration_seconds':315,
        'time_basis':'Actual placed pre-DSP protected speech start, rounded to tenths; approved pitch-only rate1 has no clock shift.',
        'output':output.name,'output_sha256':sha(output),
        'inputs':{n:sha(ROOT/n)for n in ['timeline.json','narration/placement-manifest.json','narration/ko.json','spec.json']}}
    (OUT/'narration-timeline-validation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(output)
if __name__=='__main__':main()
