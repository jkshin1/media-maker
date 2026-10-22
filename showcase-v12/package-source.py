#!/usr/bin/env python3
"""Package only the final execution sources and their bound media inputs."""
from pathlib import Path
import argparse,hashlib,json,zipfile
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parent/'out/showcase-v12'
def sha(b):return hashlib.sha256(b).hexdigest()
def include(p):
    r=p.relative_to(ROOT);s=r.as_posix()
    if '__pycache__'in r.parts or p.name.endswith('.private.json'):return False
    if r.parts[0]in ['assets','fonts','reference','baseline']:return True
    if len(r.parts)==1:return p.suffix in ['.py','.mjs','.js','.json','.md'] and p.name not in ['SOURCE_MANIFEST.json','timeline-title-preview.json','visual-restoration-review.json']
    if r.parts[0]!='narration':return False
    if len(r.parts)==2 and p.name in ['generation-settings.json']:return False
    if r.parts[1]=='elevenlabs':return p.name.startswith('complete-') or p.name=='manifest.json'
    if r.parts[1]=='transcription':return p.name in ['complete-original.json','complete-tempo1.15.json']
    if r.parts[1]in ['tail-check','recovery-proposal']:return False
    if r.parts[1]=='tone-preview':return p.name in ['plan.json','prompt.txt']
    return True
def main():
    args=argparse.ArgumentParser();args.add_argument('--final',action='store_true');a=args.parse_args()
    delivery=OUT/'delivery-validation.json'
    if not a.final:
        print(json.dumps({'ready':delivery.exists(),'action':'Use --final only after all final checks pass.'}));return
    d=json.loads(delivery.read_text());assert str(d['status']).startswith('PASS') and all(d['checks'].values())
    files=sorted(p for p in ROOT.rglob('*')if p.is_file()and include(p))
    rows=[]
    for p in files:
        b=p.read_bytes()
        assert (b'X-Goog-'+b'Signature=')not in b and (b'oob'+b'Code=')not in b, f'Signed private URL in export: {p}'
        rows.append({'file':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':sha(b)})
    identity=sha(json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
    manifest={'revision':12,'scope':'Portable final execution sources and bound inputs; private signed URL receipts and rejected incomplete audio are excluded.','source_identity_sha256':d['source_identity_sha256'],'immutable_source_identity':identity,'files':rows}
    target=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision12_Source.zip';temporary=target.with_suffix('.partial.zip')
    with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as z:
        for p,row in zip(files,rows):
            b=p.read_bytes();assert sha(b)==row['sha256'];z.writestr('showcase-v12/'+row['file'],b)
        z.writestr('showcase-v12/SOURCE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        for name in ['delivery-validation.json','final-validation.json','audio-validation.json','mux-validation.json','narration-coverage-validation.json','visual-validation.json','encoded-visual-review.json','playback-validation.json','independent-audio-validation.json','encoded-audio-validation.json','native-visual-review.json','final-mix-narration-review.json','narration-timeline-validation.json','source-reproduction-validation.json']:
            p=OUT/name
            if p.exists():z.write(p,'out/showcase-v12/'+name)
    temporary.replace(target)
    result={'revision':12,'status':'PASS','source_archive':target.name,'sha256':sha(target.read_bytes()),'bytes':target.stat().st_size,'source_files':len(rows),'immutable_source_identity':identity,'source_identity_sha256':d['source_identity_sha256']}
    (OUT/'source-package-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
