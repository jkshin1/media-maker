#!/usr/bin/env python3
"""Build readable contact sheets for all 87 existing native stills, without rendering."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

try:
    from PIL import Image,ImageDraw,ImageFont
except ImportError:
    bundled=Path('/Users/jk/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3')
    if bundled.exists() and Path(sys.executable).resolve()!=bundled.resolve():
        import os
        os.execv(str(bundled),[str(bundled),str(Path(__file__).resolve()),*sys.argv[1:]])
    raise

HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,default=HERE.parent/'out/showcase-v5')
    p.add_argument('--stills',type=Path)
    args=p.parse_args();out=args.out;stills=args.stills or out/'stills'
    visual_path=out/'visual-validation.json'
    if not visual_path.exists():
        print(json.dumps({'status':'WAIT','missing':[str(visual_path)]}));return 2
    visual=json.loads(visual_path.read_text());rows=visual['records'];timeline=json.loads((HERE/'timeline.json').read_text())
    assert len(rows)==len(timeline['entries'])==87
    missing=[str(stills/r['file']) for r in rows if not (stills/r['file']).exists()]
    if missing:print(json.dumps({'status':'WAIT','missing':missing}));return 2
    destination=out/'contact-sheets';destination.mkdir(parents=True,exist_ok=True)
    font_path=HERE/'fonts/NotoSansCJKkr-Regular.otf';font=ImageFont.truetype(str(font_path),18)
    bold=ImageFont.truetype(str(HERE/'fonts/NotoSansCJKkr-Bold.otf'),20)
    spec=json.loads((HERE/'spec.json').read_text());sections={s['id']:s for s in spec['sections']}
    records=[]
    for i,(row,e) in enumerate(zip(rows,timeline['entries'])):
        assert row['section']==e['section_id'] and row['kind']==e['kind'] and row.get('cut_index')==e.get('cut_index')
        file=stills/row['file']
        with Image.open(file) as im:assert im.size==(1920,1080)
        records.append({'entry':i+1,'file':str(file),'sha256':sha(file),'section':e['section_id'],'kind':e['kind'],'cut_id':e.get('cut_id'),'time':row['time']})
    pages=[]
    def sheet(indices,file,columns=4,width=480):
        height=round(width*1080/1920);label=58;header=44;nr=(len(indices)+columns-1)//columns
        image=Image.new('RGB',(columns*width,nr*(height+label)+header),'#101010');draw=ImageDraw.Draw(image)
        draw.text((16,10),'Revision 5 · '+str(indices[0]+1)+'–'+str(indices[-1]+1)+' / 87',font=bold,fill='#F2EEE7')
        for cell,i in enumerate(indices):
            row,e=rows[i],timeline['entries'][i];x=(cell%columns)*width;y=header+(cell//columns)*(height+label)
            with Image.open(stills/row['file']) as im:image.paste(im.convert('RGB').resize((width,height),Image.Resampling.LANCZOS),(x,y))
            section=sections[e['section_id']];cut=section['cuts'][e.get('cut_index') or 0]
            first=f"{i+1:03d}  {e['section_id']}  {e['kind']}  {e.get('cut_id') or ''}"
            second=f"{e['start']:.2f}–{e['end']:.2f}s  "+(section['title'] if e['kind']=='title' else cut.get('title',''))
            for j,text in enumerate([first,second]):
                while draw.textlength(text,font=font)>width-18 and len(text)>1:text=text[:-2]+'…'
                draw.text((x+8,y+height+3+j*25),text,font=font,fill='#F2EEE7' if j==0 else '#D4AF7C')
        target=destination/file;image.save(target);pages.append({'file':str(target),'sha256':sha(target),'entries':[i+1 for i in indices]})
    for page,start in enumerate(range(0,87,20),1):sheet(list(range(start,min(87,start+20))),'all-cuts-'+str(page).zfill(2)+'.png')
    heroes=[i for i,e in enumerate(timeline['entries']) if sections[e['section_id']]['type']!='task']
    sheet(heroes,'hero-scenes-15.png')
    sheet(list(range(87)),'overview-87.png',columns=7,width=280)
    source_hashes={f:sha(HERE/f) for f in ['spec.json','timeline.json','stage.mjs','hero-scenes.js','task-scenes.js']}
    report={'status':'READY_FOR_VISUAL_REVIEW','scope':'Contact sheets generated from all 87 native stills; no automatic aesthetic acceptance.','records':records,'pages':pages,'hero_scenes':len(heroes),'source_hashes':source_hashes}
    report_path=out/'contact-sheet-manifest.json';report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'stills':87,'hero_scenes':len(heroes),'pages':len(pages),'manifest':str(report_path)}));return 0
if __name__=='__main__':sys.exit(main())
