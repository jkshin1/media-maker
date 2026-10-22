#!/usr/bin/env python3
"""Export all exact approved wording with the final film's scene timestamps."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'out/showcase-v9'
def stamp(seconds):
    ticks=round(seconds*10);return f'{ticks//600:02d}:{(ticks%600)/10:04.1f}'
def main():
    tl=json.loads((ROOT/'timeline.json').read_text());ko=json.loads((ROOT/'narration/ko.json').read_text());spec=json.loads((ROOT/'spec.json').read_text())
    assert not tl.get('preview_only')and len(tl['audio_segments'])==68 and tl['duration']<=315
    entries={e['cut_id']:e for e in tl['entries']if e['kind']=='cut'}
    sections={s['id']:s for s in spec['sections']}
    lines=['# R&D 공정 AI Fast Track — 나레이션 타임라인','',f'기준 영상: Revision9 / 전체 길이 {stamp(tl["duration"])}','',
           '형식: 나레이션 시점: 나레이션 내용',
           '시점은 최종 영상에서 해당 멘트가 배치된 구간의 시작 시각입니다. 문구와 발화 속도를 유지했으며, 검증된 문장 사이의 긴 무음만 조정했습니다.','']
    count=0;task_number=0
    for block in ko['blocks']:
        section=sections[block['section_id']]
        title=section['title']
        if section['id']=='opening':title='오프닝'
        elif section['id']=='ending':title='엔딩'
        else:
            task_number+=1;title=f'{task_number:02d}. '+title
        owner=section.get('owner','');team=section.get('team','')
        lines+=['## '+title+(' — '+owner if owner else ''),'']
        if team:lines+=['팀: '+team,'']
        for cut in block['cuts']:
            lines.append(stamp(entries[cut['id']]['start'])+': '+cut['text']);count+=1
        lines.append('')
    assert count==68
    target=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision9_Narration_Timeline.md'
    target.write_text('\n'.join(lines),encoding='utf-8');print(target)
if __name__=='__main__':main()
