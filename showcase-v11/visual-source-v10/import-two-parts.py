#!/usr/bin/env python3
"""Download an already completed authorized two-part run; never synthesize."""
from pathlib import Path
import hashlib, json, subprocess, urllib.request, wave

ROOT=Path(__file__).resolve().parent
BASE=ROOT/'narration/two-parts'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    receipt=json.loads((BASE/'generation-result.json').read_text())
    run=json.loads((BASE/'generation-run.json').read_text())
    auth=json.loads((BASE/'authorization.json').read_text())
    plan=json.loads((ROOT/'narration/proposal-two-parts/plan.json').read_text())
    readback=json.loads((ROOT/'narration/proposal-two-parts/remote-node-readback.json').read_text())
    assert auth['authorization_source']=='direct_user_reply_in_current_chat'
    assert auth['generation_mode']=='two_part_with_user_authorization'
    assert len(run['results'])==len(plan['parts'])==2
    generations={g['id']:g for g in receipt['generations']}
    records=[]
    for i,(part,node,result) in enumerate(zip(plan['parts'],readback['nodes'],run['results']),1):
        assert part['prompt']==node['prompt'] and result['node_id']==node['node_id']
        generation_id=next(iter(result['credit_costs']))
        generation=generations[generation_id]
        assert generation['status']=='completed' and generation.get('content_url')
        assert generation['model_id']=='eleven_v4'
        projected=generation.get('prompt','')
        assert projected==part['prompt'] or (len(projected)==200 and projected==part['prompt'][:200]), 'Provider prompt projection differs from the approved proposal.'
        target=BASE/f'part{i}';target.mkdir(parents=True,exist_ok=True)
        original=target/f'generated-{generation_id}.mp3';master=target/'take.wav'
        if not original.exists():
            with urllib.request.urlopen(generation['content_url'],timeout=90) as response:
                original.write_bytes(response.read())
        if not master.exists():
            subprocess.run(['ffmpeg','-v','error','-n','-i',str(original),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(master)],check=True)
        with wave.open(str(master)) as w:
            assert (w.getframerate(),w.getnchannels(),w.getsampwidth())==(48000,1,2)
            samples=w.getnframes();pcm=w.readframes(samples)
        proof={'part_id':f'part{i}','generation_id':generation_id,'model_id':'eleven_v4','voice_id':node['voice_id'],
            'language_code':'ko','generation_mode':'two_part_with_user_authorization','authorization':'narration/two-parts/authorization.json',
            'authorization_sha256':sha(BASE/'authorization.json'),'prompt_file':f'narration/proposal-two-parts/part{i}-prompt.txt',
            'prompt_sha256':part['sha256'],'sentences':part['sentences'],'speech_tempo':1,
            'provider_receipt_prompt_is_prefix_projection':projected!=part['prompt'],
            'full_prompt_verified_against_live_node_before_run':True,
            'original_file':str(original.relative_to(ROOT)),'original_sha256':sha(original),
            'master_file':str(master.relative_to(ROOT)),'master_sha256':sha(master),'master_pcm_sha256':hashlib.sha256(pcm).hexdigest(),
            'sample_rate':48000,'channels':1,'sample_width':2,'samples':samples,'duration':samples/48000,
            'source_download_only':True,'completeness_status':'PENDING_LOCAL_TRANSCRIPTION_AND_REVIEW'}
        (target/'import-provenance.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
        records.append(proof)
    print(json.dumps(records,ensure_ascii=False))
if __name__=='__main__':main()
