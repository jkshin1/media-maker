#!/usr/bin/env python3
"""Copy approved attachments into this independent showcase and build its spec.

This importer does not generate speech, images, or video. Source attachments are
copied byte-for-byte. Timing in spec.json remains recommended, not locked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent
DEFAULT_ZIP = Path('/Users/jk/Downloads/스토리라인.zip')
DEFAULT_EXTRA = Path('/tmp/codex-remote-attachments/01a1396f-4fcc-7de0-b155-6f86911445ba/9c7c5dfd-0ad3-4fbf-89e9-972952c1aeab/1-8.RD_공정_AI_Fast_Track_이태관TL_Monitoring_Data_자연어검색_시각화_MD.md')
DEFAULT_BGM = Path('/tmp/codex-remote-attachments/01a1396f-4fcc-7de0-b155-6f86911445ba/e57975aa-ad1f-4c24-929c-2517bf842c5c/1-ES_Comprehension-Frank-Jonsson-1-.mp3')

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def import_sources(zip_path, extra, bgm):
    reference = ROOT / 'reference'
    reference.mkdir(parents=True, exist_ok=True)
    records = []
    with zipfile.ZipFile(zip_path) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            filename = Path(entry.filename).name
            if filename != entry.filename or filename in ('.', '..'):
                raise ValueError(f'Unexpected archive path: {entry.filename}')
            if Path(filename).suffix.lower() not in ('.md', '.png'):
                raise ValueError(f'Unexpected attachment type: {filename}')
            raw = archive.read(entry)
            target = reference / filename
            target.write_bytes(raw)
            records.append({'path': str(target.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha256(raw), 'source': str(zip_path), 'archive_member': entry.filename})
    # Preserve the original uploaded name including its upload prefix.
    for source, directory in ((extra, reference), (bgm, ROOT / 'assets' / 'bgm')):
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / source.name
        raw = source.read_bytes()
        target.write_bytes(raw)
        records.append({'path': str(target.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha256(raw), 'source': str(source)})
    manifest = {'zip_source': str(zip_path), 'zip_sha256': sha256(zip_path.read_bytes()), 'files': records, 'reference_md_count': sum(r['path'].endswith('.md') for r in records), 'reference_png_count': sum(r['path'].endswith('.png') for r in records), 'notes': ['Attachments imported byte-for-byte. No source attachment modified.', 'Only this independent showcase folder is written.']}
    (reference / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest

def read_sources():
    result = {}
    for path in (ROOT / 'reference').glob('*.md'):
        match = re.match(r'(?:1-)?(\d+)\.', path.name)
        if match:
            number = int(match.group(1))
            if number in result:
                raise ValueError(f'Duplicate document number: {number}')
            result[number] = (path, path.read_text(encoding='utf-8'))
    return result


# Chronological storyboard image mapping, checked against the visible images.
IMAGE_MAP = {1:'1791965410023.png', 2:'1791965410103.png', 3:'1791965410176.png', 4:'1791965410246.png', 5:'1791965410319.png', 6:'1791965410381.png', 7:'1791965410453.png', 8:'1791965410523.png', 9:'1791965410592.png', 10:'1791965410660.png', 11:'1791965410736.png', 12:'1791965410805.png', 13:'1791965410890.png', 14:'1791965410941.png', 15:'1791965410989.png', 17:'1791965411046.png', 16:'1791965411099.png', 18:'1791965411155.png'}
SECTION_ORDER = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,17,16,18]
TASK_META = {
    3:("R&D 공정 Eng'r 연구 환경 Infra 구축", '박재오 TL'),
    4:('Thinfilm Agent - BEOL Thinfilm', '김태민 TL'),
    5:('C&C Working Board Agent', '서우석 TL'),
    7:('Smart Process Architecture AI Agent', '권혜선 TL'),
    8:('Monitoring Data 자연어 검색·시각화 AI Agent', '이태관 TL'),
    9:('LLM 기반 C&C Inline Data 분석 AI Agent', '윤지욱 TL'),
    11:('RSAB SNM Overlay 열화 원인 분석 및 솔루션 제시 Agent', '장민희 TL'),
    12:('경비 분석 및 절감 아이템 발굴 Agent 개발', '오승재 TL'),
    13:('장비 Daily Report Auto Mail System', '김도훈 TL'),
    14:('Cubic공정Lab 전용 App&Agent', '정현준 TL'),
    17:('TCAD-TEM 이미지 연계를 통한 이미지 Labeling Tool 개발', '김성후 TL'),
    16:('AI Agent 기반 Plug 대면적 데이터 분석 자동화 및 인사이트 도출', '김지은 TL'),
}
SUMMARY_META = {
    2:('summary1', ['흩어진 정보를 연결해', '더 넓은 가능성을 열다'], ['AI가 다양한 데이터와 지식을 연결해', '더 정확하고 빠른 R&D 인사이트를 만듭니다.']),
    6:('summary2', ['필요한 지식을 찾아', '업무에 활용하다'], ['흩어진 정보 속에서 필요한 지식을 찾고,', '관련 데이터와 연결해 더 나은 업무 판단을 지원합니다.']),
    10:('summary3', ['반복 업무를 줄이고', '분석에 집중하다'], ['데이터 분석과 반복 업무 자동화로', '더 효율적인 R&D 환경을 만듭니다.']),
    15:('summary4', ['이미지와 데이터를 분석해', '더 정교한 연구를 실현하다'], ['이미지 측정과 대규모 데이터 분석을 효율화해', '더 신뢰도 높은 연구 결과를 지원합니다.']),
}

def plain(s):
    """Remove markup while retaining exact Korean words and punctuation."""
    s = re.sub(r'^\s*>\s?', '', s, flags=re.M)
    s = s.replace('**', '').replace('`', '')
    s = re.sub(r'^\s*[-*]\s+', '', s, flags=re.M)
    return s.strip().strip('“”"').strip()

def fields(block):
    # A field label occupies its own line, optionally with an inline value.
    matches = list(re.finditer(r'^\*\*([^*\n]+)\*\*(.*)$', block, re.M))
    result = {}
    for i,m in enumerate(matches):
        label = m.group(1).strip().rstrip(':：')
        # Bold inside quotes is content, not a field label.
        if label.startswith(('12개의 도전', '이제 두')):
            continue
        end = matches[i+1].start() if i+1<len(matches) else len(block)
        value = m.group(2).strip() + '\n' + block[m.end():end]
        result[label] = value.strip().removesuffix('---').strip()
    return result

def segment_blocks(source):
    matches = list(re.finditer(r'^###\s+((?:CUT|SCENE)\s+\d+)\s+[—–-]\s+(.+)$', source, re.M))
    segments=[]
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(source)
        major=re.search(r'^##\s', source[m.end():end], re.M)
        if major:
            end=m.end()+major.start()
        segments.append((m.group(1),m.group(2),source[m.end():end].strip()))
    return segments

def time_range(s):
    m=re.search(r'(\d+(?:\.\d+)?)\s*[~–—-]\s*(\d+(?:\.\d+)?)\s*초',s)
    return [float(m[1]),float(m[2])] if m else None

def all_narration(number, source):
    if number in (3,4,5):
        anchor = {3:'### 확정 나레이션 전체본',4:'### 전체 나레이션',5:'## 3. 전체 나레이션'}[number]
        tail=source[source.index(anchor)+len(anchor):]
        return re.search(r'“([^”]+)”',tail,re.S)[1].strip()
    anchor=re.search(r'^##\s+\d+\.\s+(?:나레이션 전체본|나레이션 전체 원고|내레이션 전체 원고|전체 나레이션 원고)',source,re.M)
    if not anchor:
        return ''
    tail=source[anchor.end():]
    stop=re.search(r'^##\s',tail,re.M)
    if stop:
        tail=tail[:stop.start()]
    return [plain(m[1]) for m in re.finditer(r'^\d+\.\s+(.+)$',tail,re.M)]

def restriction_text(source):
    snippets=[]
    for match in re.finditer(r'^##\s+\d+\.\s+([^\n]*(?:정확성|금지|필수 구현)[^\n]*)', source, re.M):
        rest=source[match.end():]
        stop=re.search(r'^##\s',rest,re.M)
        snippets.append(rest[:stop.start()] if stop else rest)
    return '\n'.join(snippets).strip()

def summary_cuts(source, section_id):
    matches=list(re.finditer(r'^###\s+(\d+(?:\.\d+)?)\s*[–~-]\s*(\d+(?:\.\d+)?)초\s+[—–-]\s+(.+)$',source,re.M))
    result=[]
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(source)
        block=source[m.end():end]
        stop=re.search(r'^##\s',block,re.M)
        if stop: block=block[:stop.start()]
        result.append({'id':f'{section_id}_event{i+1}', 'title':m[3].strip(), 'caption':'', 'narration':'', 'recommended_seconds':float(m[2])-float(m[1]), 'recommended_range_seconds':[float(m[1]),float(m[2])], 'motion':block.strip(), 'visual':block.strip()})
    return result

def make_spec(sources, bgm):
    sections=[]
    global_deviations=[]
    quantitative_replacements={
        12:('분석 시간을 80% 이상 줄이고 더 효율적인 예산 운영을 지원합니다.', '분석 시간을 줄이고 더 효율적인 예산 운영을 지원합니다.', 'MD 7항: 시안 수치는 원본 자료 확인 후 사용. 승인된 원본 성과 자료가 첨부되지 않아 80% 수치를 제외했습니다.'),
        14:('업무 시간을 90% 이상 단축합니다.', '업무 시간을 단축합니다.', 'MD 7항: 90% 이상 단축은 승인된 자료에서 확인되는 경우에만 사용. 별도 원자료가 없어 정량 부분을 제외했습니다.'),
        17:('이미지당 측정 시간은 5분에서 6초로 줄고, R_NIT 정확도는 44%, S/W 정확도는 84% 개선됩니다.', '이미지당 측정 시간은 줄고, R_NIT와 S/W 정확도는 개선됩니다.', 'MD 7항: 5분→6초, R_NIT 44%, S/W 84%는 승인된 원본 자료에서 확인되는 경우에만 사용. 별도 원자료가 없어 정량 부분을 제외했습니다.'),
    }
    for number in SECTION_ORDER:
        path,source=sources[number]
        is_summary=number in SUMMARY_META
        kind='summary' if is_summary else 'task' if number in TASK_META else 'opening' if number==1 else 'ending'
        section_id=SUMMARY_META[number][0] if is_summary else f'task{number}' if kind=='task' else kind
        title,owner=TASK_META.get(number,(plain(source.splitlines()[0].lstrip('# ')),''))
        section={'id':section_id,'type':kind,'title':title,'owner':owner,'source_md':str(path.relative_to(ROOT)),'source_number':number,'reference_image':'reference/'+IMAGE_MAP[number], 'cuts':[], 'restrictions':restriction_text(source),'deviations':[]}
        if kind=='task':
            section['title_card']={'title':title,'owner':owner,'recommended_seconds':2.0,'narration':'','note':'Separate short editable title card; actual timing to be set after voice alignment.'}
        if is_summary:
            _,main,support=SUMMARY_META[number]
            section['main_lines']=main
            section['support_lines']=support
            section['cuts']=summary_cuts(source,section_id)
            section['recommended_seconds']=8
        else:
            overall=all_narration(number,source)
            blocks=segment_blocks(source)
            expected=9 if number==1 else 6 if number==18 else 5
            if len(blocks)!=expected:
                raise ValueError(f'{section_id}: expected {expected} cuts, got {len(blocks)}')
            for i,(source_cut,heading,block) in enumerate(blocks):
                f=fields(block)
                timing=time_range(heading) or time_range(f.get('권장 시간',''))
                scene_title=re.sub(r'\s*\([^)]*초\)\s*$','',heading).strip()
                visual='\n'.join(f.get(key,'') for key in ('화면','화면 구성','화면 목적','질문 문구') if f.get(key))
                if not visual: visual=block
                motion='\n'.join(f.get(key,'') for key in ('모션 상세 지시','모션을 반드시 구현','모션','카메라·모션','전환') if f.get(key))
                # Where a display headline is explicitly specified, use it.
                display=plain(f.get('장면 제목',f.get('화면 자막','')))
                if not display:
                    match=re.search(r'(?:상단 제목|화면 상단 제목|화면 문구|제목):\s*`([^`]+)`',visual)
                    display=match[1] if match else scene_title
                screen_field=f.get('화면 문구',f.get('화면 문구 및 보조 항목',f.get('메인 문구','')))
                screen_lines=re.findall(r'`([^`]+)`',screen_field)
                if not screen_lines and screen_field and plain(screen_field)!='없음':
                    screen_lines=[plain(l) for l in screen_field.splitlines() if plain(l)]
                raw_voice=plain(f.get('나레이션',f.get('내레이션',''))).replace('…','').strip()
                if '나레이션 없음' in raw_voice: raw_voice=''
                if isinstance(overall,list):
                    raw_voice=overall[i] if number!=18 else overall[{0:0,1:1,2:2,4:3}.get(i,0)] if i in (0,1,2,4) else ''
                if number==4 and i==3:
                    raw_voice='이어서 '+raw_voice
                cut={'id':f'{section_id}_cut{i+1}','title':display,'scene_title':scene_title,'caption':raw_voice,'narration':raw_voice,'source_narration':raw_voice,'recommended_seconds':timing[1]-timing[0] if timing else (7.5 if number in (11,16,17) else 6.5),'motion':motion,'visual':visual,'screen_lines':screen_lines,'support_lines':re.findall(r'`([^`]+)`',f.get('보조 문구','')),'source_cut':source_cut}
                cut['show_title']=kind=='task'
                cut['source_fields']=f
                cut['ui_labels']=list(dict.fromkeys(re.findall(r'`([^`]+)`',visual)))
                if not cut['support_lines'] and f.get('보조 문구'):
                    cut['support_lines']=[plain(l) for l in f['보조 문구'].splitlines() if plain(l)]
                if f.get('질문 문구'):
                    questions=re.findall(r'`([^`]+)`',f['질문 문구'])
                    if questions: cut['question']=questions[0]
                if timing: cut['recommended_range_seconds']=timing
                else: cut['recommended_basis']='Equal share of MD section duration; MD does not specify per-cut timings. Final timings require narration alignment.'
                if number in quantitative_replacements and i==4:
                    original,replacement,reason=quantitative_replacements[number]
                    if raw_voice!=original:
                        raise ValueError(f'Unexpected conditional narration in {section_id}: {raw_voice}')
                    cut['caption']=cut['narration']=replacement
                    d={'cut_id':cut['id'],'field':'narration and matching subtitle','original':original,'replacement':replacement,'reason':reason}
                    section['deviations'].append(d)
                    global_deviations.append(d)
                    cut['screen_lines']=[]
                section['cuts'].append(cut)
            # This detects accidentally duplicated or lost narration fragments.
            original_join=' '.join(c['source_narration'] for c in section['cuts'] if c['source_narration'])
            authoritative=' '.join(overall) if isinstance(overall,list) else overall
            def compact(s): return re.sub(r'\s+','',s).replace('…','').replace('...','')
            if compact(original_join)!=compact(authoritative):
                raise ValueError(f'{section_id}: cut narration does not reproduce full approved script:\n{original_join}\nVERSUS\n{authoritative}')
            section['source_full_narration']=authoritative
            section['full_narration']=' '.join(c['narration'] for c in section['cuts'] if c['narration'])
            section['recommended_seconds']=sum(c['recommended_seconds'] for c in section['cuts'])
            if number==18:
                section['cuts'][-1]['cards']=[{'owner':'김지은 TL','title':TASK_META[16][0],'reference_image':'reference/'+IMAGE_MAP[16]},{'owner':'장민희 TL','title':TASK_META[11][0],'reference_image':'reference/'+IMAGE_MAP[11]}]
                section['cuts'][-1]['source_motion']=section['cuts'][-1]['motion']
                section['cuts'][-1]['motion']=section['cuts'][-1]['motion'].replace('김지은 TL 과제 영상의 시작 타이틀로 전환한다.','현장 발표로 자연스럽게 전환한다.')
                section['transition_after']='End the file; hand over to the live presenter, per integrated MD 19.'
            section['conditional_metric_exclusions']={8:['40% 이상 단축'],9:['70% 이상 단축'],11:['분석 시간 15분~1시간 → 건당 수분'],12:['분석 시간 80% 이상 단축','경비 실적 14,000건 이상','장비 이력 18,000건 이상'],14:['업무 시간 90% 이상 단축'],17:['5분 → 6초','R_NIT 44% 개선','S/W 84% 개선']}.get(number,[])
        sections.append(section)
    spec={'output':{'filename':'out/RD_Process_AI_Fast_Track_Showcase.mp4','width':1920,'height':1080,'fps':30,'video_codec':'H.264','audio_codec':'AAC','max_seconds':300,'timing_status':'recommended_only; parent locks timing after narration alignment','bgm':str((ROOT/'assets'/'bgm'/bgm.name).relative_to(ROOT))},'title':'R&D 공정 AI Fast Track 성과공유회','sections':sections,'deviations':global_deviations,'source_policy':{'order':'Integrated MD 19; TCAD (17) then Plug (16), then separate ending.','names':'Latest uploaded MD values, including 박재오 TL.','conditional_metrics':'Omit metrics that the task MD expressly conditions on separate original evidence; retain remaining wording.','source_images':'Reference art only. Rebuild motion and exact editable Korean text.','ending':'No extra task videos after the ending; ending cuts 4 and 6 have no narration.'},'palette':{'black':'#080808','charcoal':'#1A1A1F','gold':'#D4AF7C','light_gold':'#F5D6A6','amber':'#FFB347','cream':'#F2EEE7'}}
    (ROOT/'spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return spec


def make_crops(spec):
    """Crop only photographic/texture regions, never a full storyboard panel.

    These low-resolution reference crops are for backgrounds and photo textures.
    Their metadata explicitly distinguishes them from actual task data/screens.
    Motion and all text are to be rebuilt by the renderer.
    """
    from PIL import Image
    directory=ROOT/'assets'/'crops'
    directory.mkdir(parents=True,exist_ok=True)
    # Manually inspected rectangles exclude storyboard headers and captions.
    # Small text in photographed spreadsheets remains part of the photographed
    # screen, with no added descriptive labels or claimed analytical results.
    before_rects={3:(0,560,333,766),4:(2,299,112,636),5:(1370,574,1670,673),7:(0,372,252,500),8:(0,661,180,849),9:(0,719,342,849),11:(0,566,357,778),12:(0,568,324,780),13:(0,640,348,772),14:(0,659,326,779),17:(0,578,336,759),16:(0,548,308,756)}
    # Per-task supporting photographed wafer/lab/detail crops, where available.
    after_rects={3:None,4:None,5:(1370,574,1670,673),7:(1405,777,1671,939),8:(1480,720,1670,848),9:(1390,703,1670,848),11:None,12:None,13:(1475,280,1670,565),14:(1404,242,1670,526),17:(1486,223,1668,319),16:None}
    records=[]
    def crop(section_id, name, box, source_number, note):
        filename=f'{section_id}-{name}.png'
        source=ROOT/'reference'/IMAGE_MAP[source_number]
        with Image.open(source) as im:
            extracted=im.crop(box)
            extracted.save(directory/filename)
            size=extracted.size
        record={'path':'assets/crops/'+filename,'source':'reference/'+source.name,'rect_xyxy':list(box),'size':list(size),'source_kind':'approved concept image; not independently verified task data','note':note,'sha256':sha256((directory/filename).read_bytes())}
        records.append(record)
        return record['path']
    for section in spec['sections']:
        n=section['source_number']
        if n not in TASK_META: continue
        before=crop(section['id'],'before-photo',before_rects[n],n,'Photographic region only; excludes storyboard title and narration. Photographed screen texture may contain unreadably small source text.')
        after=crop(section['id'],'after-photo',after_rects[n],n,'Small photographic detail; excludes storyboard headline and narration. Do not present as a verified task screenshot.') if after_rects[n] else None
        section['backgrounds']=[before,after,after,after,after]
    microscopy={}
    microscopy['task17']=crop('task17','micrograph',(4,288,71,449),17,'Text-free grayscale TEM texture from first reference panel; no measurement values. Low-resolution concept texture.')
    microscopy['task16']=crop('task16','micrograph',(813,320,931,442),16,'Text-free grayscale circular Plug image texture; fine source crosshair retained, no classification label or numeric values.')
    opening_boxes=[(0,60,152,207),(565,51,890,204),(1123,47,1461,208),(1,294,356,474),None,(1122,300,1514,472),(0,560,357,740),(565,563,891,740),(1122,559,1358,741)]
    opening=next(s for s in spec['sections'] if s['type']=='opening')
    opening['backgrounds']=[crop('opening',f'photo{i+1}',box,1,'Text-free reference scene region; all opening text rebuilt separately.') if box else None for i,box in enumerate(opening_boxes)]
    for section in spec['sections']:
        if section['type']=='summary':
            path=crop(section['id'],'wafer',(425,570,1240,917),section['source_number'],'Lower central wafer photographic region; excludes center message and UI headers.')
            section['backgrounds']=[path]*len(section['cuts'])
    spec['microscopy']=microscopy
    # Remove outputs from a previous crop pass whose regions were rejected at QA.
    approved={Path(record['path']).name for record in records}
    for stale in directory.glob('*.png'):
        if stale.name not in approved: stale.unlink()
    crop_manifest={'files':records,'note':'Crops contain photographed surfaces/people/screens/wafer details only. Never use as stationary panels; rebuild each requested UI motion and text. Source resolution limits quality.'}
    (directory/'manifest.json').write_text(json.dumps(crop_manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return len(records)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--zip', type=Path, default=DEFAULT_ZIP)
    parser.add_argument('--extra-md', type=Path, default=DEFAULT_EXTRA)
    parser.add_argument('--bgm', type=Path, default=DEFAULT_BGM)
    parser.add_argument('--crops', action='store_true',help='Requires Pillow; generate cropped photographic source regions.')
    args = parser.parse_args()
    manifest = import_sources(args.zip, args.extra_md, args.bgm)
    sources = read_sources()
    spec=make_spec(sources,args.bgm)
    crop_count=make_crops(spec) if args.crops else 0
    print(json.dumps({'imported_markdown': manifest['reference_md_count'], 'imported_png': manifest['reference_png_count'], 'document_numbers': sorted(sources), 'sections':len(spec['sections']),'cuts':sum(len(s['cuts']) for s in spec['sections']), 'narration_characters':sum(len(c['narration']) for s in spec['sections'] for c in s['cuts']), 'photographic_crops':crop_count,'bgm': str((ROOT/'assets'/'bgm'/args.bgm.name).relative_to(ROOT))}, ensure_ascii=False))

if __name__ == '__main__':
    main()
