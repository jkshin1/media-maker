#!/usr/bin/env python3
"""Copy clean, locally approved photographic plates without changing sources."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 spec=json.loads((HERE/'spec.json').read_text());records=[]
 for i in range(1,10):
  stem=f'cut{i:02d}';src=ROOT/'opening-v3/assets'/f'{stem}-clean.png'
  if not src.exists():src=ROOT/'opening-v3/assets'/f'{stem}.png'
  dst=HERE/'assets/opening'/f'{stem}.png';dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
  records.append({'file':str(dst.relative_to(HERE)),'source':str(src.relative_to(ROOT)),'sha256':sha(dst),'role':'Clean photographic plate matching the same nine opening concepts; editable text is drawn separately.'})
 # The supplied boards contain small photographic thumbnails. Keep the new
 # reference crops in after shots; use approved task-specific high-resolution
 # manual-work photos for BEFORE and title backgrounds to preserve clarity.
 mapping={'task3':6,'task4':3,'task5':4,'task7':1,'task8':8,'task9':5,'task11':11,'task12':7,'task13':2,'task14':10,'task17':9,'task16':12}
 for section in spec['sections']:
  if section['id'] not in mapping:continue
  src=ROOT/'production/assets/before'/f'task-{mapping[section["id"]]:02d}.png'
  dst=HERE/'assets/before'/f'{section["id"]}.png';dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
  section['backgrounds'][0]=str(dst.relative_to(HERE))
  records.append({'file':str(dst.relative_to(HERE)),'source':str(src.relative_to(ROOT)),'sha256':sha(dst),'role':'Task-specific manual-work photograph; supplied-board composition retained for UI/content shots.'})
 fonts=HERE/'fonts';fonts.mkdir(exist_ok=True)
 for src in (ROOT/'opening-v3/fonts').glob('*'):
  if src.is_file():shutil.copy2(src,fonts/src.name)
 (HERE/'spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
 (HERE/'supplemental-assets.json').write_text(json.dumps({'sources_unchanged':True,'assets':records},ensure_ascii=False,indent=2)+'\n')
 print('Prepared',len(records),'photographic plates')
if __name__=='__main__':main()
