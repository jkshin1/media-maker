#!/usr/bin/env python3
"""Package executable sources and local assets, omitting ephemeral signed URLs."""
from pathlib import Path
import hashlib,json,zipfile
HERE=Path(__file__).resolve().parent;OUT=HERE.parent/'out/showcase-v8'
def clean(value):
 if isinstance(value,dict):return {k:clean(v) for k,v in value.items() if k!='url' and not k.endswith('_url')}
 if isinstance(value,list):return [clean(v) for v in value]
 return value
def main():
 completed=(OUT/'RD_Process_AI_Fast_Track_Showcase_Revision8.mp4').exists() and (OUT/'final-validation.json').exists()
 if completed:completed=json.loads((OUT/'final-validation.json').read_text()).get('status')=='PASS'
 suffix='Source'if completed else'Draft_Source'
 target=OUT/f'RD_Process_AI_Fast_Track_Showcase_Revision8_{suffix}.zip';inventory=[]
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(HERE.rglob('*')):
   if not p.is_file() or any(v in {'node_modules','__pycache__','.DS_Store'} for v in p.relative_to(HERE).parts):continue
   data=p.read_bytes();relative=str(p.relative_to(HERE));
   if relative.startswith('narration/') and p.suffix=='.json' and any(v in p.name for v in ('receipt','generation')):
    data=(json.dumps(clean(json.loads(data)),ensure_ascii=False,indent=2)+'\n').encode()
   z.writestr('showcase-v8/'+relative,data);inventory.append({'file':'showcase-v8/'+relative,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
  for name in ['SOURCE_STATUS.json','NARRATION_STATUS.json','baseline-preservation-validation.json','visual-review-render-validation.json','visual-review-decode-validation.json','visual-review-playback-validation.json','final-validation.json','render-validation.json','visual-validation.json','revision8-content-validation.json','camera-validation.json','narration-script-review.json','narration-coverage-validation.json','independent-audio-review.json','independent-audio-envelope.json','encoded-audio-validation.json','native-visual-review.json','encoded-visual-review.json','playback-validation.json','mux-validation.json','audio-validation.json','source-reproduction-validation.json','source-package-validation.json','SHA256SUMS.txt']:
   p=OUT/name
   if p.exists():
    data=p.read_bytes();relative='out/showcase-v8/'+name;z.writestr(relative,data);inventory.append({'file':relative,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'kind':'validation_receipt'})
  z.writestr('SOURCE_MANIFEST.json',json.dumps({'production_complete':completed,'delivery_status':'FINAL'if completed else'VISUAL_PREVIEW_ONLY_NARRATION_PENDING','files':inventory,'signed_generation_urls_omitted':True},ensure_ascii=False,indent=2)+'\n')
 with zipfile.ZipFile(target) as z:assert z.testzip() is None
 print(json.dumps({'file':str(target),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'source_files':len(inventory)}))
if __name__=='__main__':main()
