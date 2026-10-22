#!/usr/bin/env python3
"""Download already generated, authorized two-part audio. Never generate speech."""
from pathlib import Path
import argparse,hashlib,json,subprocess,urllib.request,wave
ROOT=Path(__file__).resolve().parent
def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--fetch',action='store_true');args=p.parse_args()
    proposal=json.loads((ROOT/'narration/recovery-proposal/plan.json').read_text())
    receipt=json.loads((ROOT/'narration/two-parts/completed-receipt.private.json').read_text())
    authpath=ROOT/'narration/two-parts/authorization.json';auth=json.loads(authpath.read_text())
    assert auth['authorization_source']=='direct_user_reply_in_current_chat' and auth['two_part_exception_authorized'] and auth['generations_count_each']==1
    assert receipt['all_completed'] and not receipt['has_failures'] and len(receipt['generations'])==2
    ids=[next(iter(r['credit_costs'])) for r in receipt['run_results']]
    parts=[]
    for row,genid in zip(proposal['parts'],ids):
        generation=next(g for g in receipt['generations']if g['id']==genid)
        assert generation['status']=='completed' and generation['model_id']==auth['model_id']
        directory=ROOT/'narration/two-parts'/row['part_id'];directory.mkdir(exist_ok=True)
        mp3=directory/f'generated-{genid}.mp3';master=directory/'take.wav';prompt=directory/'prompt.txt'
        assert prompt.read_text()==row['prompt']+'\n'
        if not mp3.exists():
            assert args.fetch,'Use --fetch to download the already completed generation.'
            with urllib.request.urlopen(generation['content_url'],timeout=60)as response:content=response.read()
            assert len(content)>100000;mp3.write_bytes(content)
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(mp3),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(master)],check=True)
        with wave.open(str(master))as stream:params=stream.getparams();pcm=stream.readframes(params.nframes)
        proof={'part_id':row['part_id'],'generation_id':genid,'voice_id':auth['voice_id'],'model_id':auth['model_id'],'generation_mode':auth['generation_mode'],'generations_count':1,'tone_preview_selected':4,'tone_generation_id':auth['selected_generation_id'],'cut_ids':row['cut_ids'],'sentence_count':len(row['cut_ids']),'prompt_file':prompt.relative_to(ROOT).as_posix(),'prompt_sha256':sha(prompt.read_bytes()),'prompt_payload_sha256':sha(row['prompt'].encode()),'original_file':mp3.relative_to(ROOT).as_posix(),'original_sha256':sha(mp3.read_bytes()),'master':master.relative_to(ROOT).as_posix(),'master_sha256':sha(master.read_bytes()),'master_pcm_sha256':sha(pcm),'sample_rate':params.framerate,'channels':params.nchannels,'sample_width':params.sampwidth,'samples':params.nframes,'seconds':params.nframes/params.framerate,'speech_tempo_on_raw':1,'pitch_cents':0,'authorization':{'path':authpath.relative_to(ROOT).as_posix(),'sha256':sha(authpath.read_bytes())},'provider_price':generation['price'],'completeness':'PENDING_LOCAL_ASR'}
        save(directory/'import-provenance.json',proof);parts.append(proof)
    save(ROOT/'narration/two-parts/import-summary.json',{'generation_mode':auth['generation_mode'],'parts':parts,'actual_generations':2,'retries':0,'total_sentences_expected':68})
    print(json.dumps({'parts':[{k:r[k]for k in ['part_id','generation_id','samples','seconds','master_sha256']}for r in parts],'actual_generations':2},ensure_ascii=False))
if __name__=='__main__':main()
