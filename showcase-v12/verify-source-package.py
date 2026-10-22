#!/usr/bin/env python3
"""Verify the archive inventory and reproduce all four delivered WAVs offline."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,os,subprocess,sys,tempfile,wave,zipfile
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parent/'out/showcase-v12'
def sha(b):return hashlib.sha256(b).hexdigest()
def pcm(p):
    with wave.open(str(p))as w:return sha(w.readframes(w.getnframes()))
def main():
    p=argparse.ArgumentParser();p.add_argument('--package-only',action='store_true');a=p.parse_args()
    archive=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision12_Source.zip';checks={}
    with zipfile.ZipFile(archive)as z:
        names=z.namelist();checks['unique_safe_paths']=len(names)==len(set(names))and all(not PurePosixPath(n).is_absolute()and'..'not in PurePosixPath(n).parts for n in names)
        assert checks['unique_safe_paths'];checks['CRC']=z.testzip()is None
        manifest=json.loads(z.read('showcase-v12/SOURCE_MANIFEST.json'));rows=manifest['files'];checks['exact_source_inventory']=set(n for n in names if n.startswith('showcase-v12/'))=={'showcase-v12/'+r['file']for r in rows}|{'showcase-v12/SOURCE_MANIFEST.json'}
        checks['source_hashes_and_sizes']=all(len(z.read('showcase-v12/'+r['file']))==r['bytes']and sha(z.read('showcase-v12/'+r['file']))==r['sha256']for r in rows)
        checks['no_private_signed_urls']=all((b'X-Goog-'+b'Signature=')not in z.read(n)and (b'oob'+b'Code=')not in z.read(n)for n in names)
        checks['immutable_source_identity']=sha(json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())==manifest['immutable_source_identity']
        assert all(checks.values()),checks
        matches=[];still_matches=[];working=None
        if a.package_only:
            prior=json.loads((OUT/'source-reproduction-validation.json').read_text())
            checks['prior_fresh_reproduction_PASS']=prior['status']=='PASS'and all(prior['checks'].values())
            checks['same_immutable_source_as_fresh_reproduction']=prior['immutable_source_identity']==manifest['immutable_source_identity']
            assert all(checks.values()),checks
        if not a.package_only:
            working=Path(tempfile.mkdtemp(prefix='showcase-v12-source-check-',dir='/private/tmp'));z.extractall(working)
            script=working/'showcase-v12/audio.py';python=os.environ.get('AUDIO_PYTHON',sys.executable)
            run=subprocess.run([python,str(script)],capture_output=True,text=True,check=True)
            for name in ['narration-raw.wav','narration.wav','bgm-loop.wav','audio.wav']:
                q=working/'out/showcase-v12'/name;r=OUT/name
                matches.append({'file':name,'file_equal':sha(q.read_bytes())==sha(r.read_bytes()),'pcm_equal':pcm(q)==pcm(r),'sha256':sha(q.read_bytes())})
            checks['fresh_offline_audio_build']=True;checks['four_WAV_file_and_PCM_exact']=len(matches)==4 and all(r['file_equal']and r['pcm_equal']for r in matches)
            node=os.environ.get('NODE_BINARY','node')
            subprocess.run([node,str(working/'showcase-v12/render.mjs'),'--stills'],capture_output=True,text=True,check=True)
            original_stills=sorted((OUT/'stills').glob('*.png'))
            for original in original_stills:
                reproduced=working/'out/showcase-v12/stills'/original.name
                still_matches.append({'file':original.name,'equal':reproduced.exists()and sha(reproduced.read_bytes())==sha(original.read_bytes())})
            checks['fresh81stills_exact']=len(still_matches)==81 and all(r['equal']for r in still_matches)
            checks['fresh_build_preserves_all_source_bytes']=all((working/'showcase-v12'/r['file']).is_file()and sha((working/'showcase-v12'/r['file']).read_bytes())==r['sha256']for r in rows)
    result={'revision':12,'status':'PASS'if all(checks.values())else'FAIL','archive_sha256':sha(archive.read_bytes()),'immutable_source_identity':manifest['immutable_source_identity'],'checks':checks,'WAV_matches':matches,'stills_reproduced':len(still_matches),'stills_exact_matches':sum(r['equal']for r in still_matches),'fresh_directory':str(working)if working else None,'package_only':a.package_only,'scope':('Archive-only CRC/SHA/inventory checks and identity equality to the prior fresh reproduction; no WAV/PNG build repeated.'if a.package_only else'Archive inventory/CRC/SHA, offline saved-input4WAV and81PNG reproduction, and unchanged source bytes after build; no full-video re-rendering, new speech generation or subjective voice acceptance claimed.')}
    target=OUT/('source-package-final-verification.json'if a.package_only else'source-reproduction-validation.json');target.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert result['status']=='PASS'
if __name__=='__main__':main()
