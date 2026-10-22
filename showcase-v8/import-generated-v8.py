#!/usr/bin/env python3
"""Import the already completed provider file; never generates speech."""
from pathlib import Path
import argparse,hashlib,json,subprocess,urllib.request,wave
ROOT=Path(__file__).resolve().parent
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--receipt',required=True);parser.add_argument('--out',default='narration/elevenlabs');parser.add_argument('--prompt',default='narration/tasks-prompt.txt');parser.add_argument('--scope',default='twelve_task_single_take');args=parser.parse_args()
 receipt=json.loads((ROOT/args.receipt).read_text())
 generation=next(g for g in receipt['generations']if g['status']=='completed' and g.get('content_url'))
 target=ROOT/args.out;target.resolve().relative_to(ROOT.resolve());target.mkdir(parents=True,exist_ok=True)
 original=target/f"generated-{generation['id']}.mp3";master=target/'take.wav'
 if not original.exists():
  with urllib.request.urlopen(generation['content_url'],timeout=60)as response:original.write_bytes(response.read())
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(original),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(master)],check=True)
 with wave.open(str(master))as f:params=f.getparams()
 config=json.loads((ROOT/'narration/tasks-ko.json').read_text())
 proof={'generation_id':generation['id'],'model_id':generation['model_id'],'voice_id':config['voice_id'],'voice_name':config['voice_name'],'prompt_file':args.prompt,'prompt_sha256':hashlib.sha256((ROOT/args.prompt).read_bytes()).hexdigest(),'generation_mode':'single_project_take'if args.scope=='task16_replacement'else'single_take','scope':args.scope,'original_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'master_sha256':hashlib.sha256(master.read_bytes()).hexdigest(),'sample_rate':params.framerate,'channels':params.nchannels,'samples':params.nframes,'duration':params.nframes/params.framerate,'settings_scope':'Connector selected voice and model; additional saved voice settings are not exposed by this speech tool and are not claimed as independently applied.'}
 (target/'import-provenance.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(proof,ensure_ascii=False))
if __name__=='__main__':main()
