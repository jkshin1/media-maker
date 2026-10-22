#!/usr/bin/env python3
"""Package executable sources and local assets, omitting ephemeral signed URLs."""
from pathlib import Path
import hashlib,json,zipfile
HERE=Path(__file__).resolve().parent;OUT=HERE.parent/'out/showcase-v5'
def clean(value):
 if isinstance(value,dict):return {k:clean(v) for k,v in value.items() if k not in {'url','flow_url','content_url','master_url','preview_url','thumbnail_url','orb_url'}}
 if isinstance(value,list):return [clean(v) for v in value]
 return value
def main():
 target=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision5_Source.zip';inventory=[]
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(HERE.rglob('*')):
   if not p.is_file() or any(v in {'node_modules','__pycache__','.DS_Store'} for v in p.relative_to(HERE).parts):continue
   data=p.read_bytes();relative=str(p.relative_to(HERE));
   if relative.startswith('narration/') and p.suffix=='.json' and any(v in p.name for v in ('receipt','generation-result','generation-failure')):
    data=(json.dumps(clean(json.loads(data)),ensure_ascii=False,indent=2)+'\n').encode()
   z.writestr('showcase-v5/'+relative,data);inventory.append({'file':'showcase-v5/'+relative,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
  for name in ['final-validation.json','render-validation.json','visual-validation.json','source-visual-review.json','visual-review.json','encoded-visual-review.json','playback-validation.json','mux-validation.json','audio-validation.json','bgm-audit-before.json','bgm-audit.json','audio-reproduction-validation.json','final-speech-review.json','contact-sheet-manifest.json','source-reproduction-validation.json','source-package-validation.json','SHA256SUMS.txt']:
   p=OUT/name
   if p.exists():z.writestr('out/showcase-v5/'+name,p.read_bytes())
  z.writestr('SOURCE_MANIFEST.json',json.dumps({'files':inventory,'signed_generation_urls_omitted':True},ensure_ascii=False,indent=2)+'\n')
 with zipfile.ZipFile(target) as z:assert z.testzip() is None
 print(json.dumps({'file':str(target),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'source_files':len(inventory)}))
if __name__=='__main__':main()
