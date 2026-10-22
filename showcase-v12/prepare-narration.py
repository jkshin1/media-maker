#!/usr/bin/env python3
"""Assemble the two raw originals exactly, then apply authorized tempo once."""
from pathlib import Path
import hashlib,json,subprocess,wave
ROOT=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def read(p):
    with wave.open(str(p))as w:
        assert(w.getframerate(),w.getnchannels(),w.getsampwidth())==(48000,1,2)
        return w.getnframes(),w.readframes(w.getnframes())
def main():
    authfile=ROOT/'narration/two-parts/authorization.json';auth=json.loads(authfile.read_text());summary=json.loads((ROOT/'narration/two-parts/import-summary.json').read_text())
    assert auth['speech_tempo']==1.15 and auth['pitch_cents']==0 and auth['two_part_exception_authorized']
    rows=summary['parts'];assert[len(r['cut_ids'])for r in rows]==[33,35]
    ko=json.loads((ROOT/'narration/ko.json').read_text());assert[c for r in rows for c in r['cut_ids']]==[c['id']for b in ko['blocks']for c in b['cuts']]
    chunks=[];cursor=0
    for r in rows:
        f=ROOT/r['master'];n,pcm=read(f);assert sha(f.read_bytes())==r['master_sha256'] and sha(pcm)==r['master_pcm_sha256'] and n==r['samples']
        r['virtual_start_sample']=cursor;r['virtual_end_sample']=cursor+n;cursor+=n;chunks.append(pcm)
    composite=ROOT/'narration/elevenlabs/complete-original.wav';composite.parent.mkdir(exist_ok=True);pcm=b''.join(chunks)
    with wave.open(str(composite),'wb')as w:w.setframerate(48000);w.setnchannels(1);w.setsampwidth(2);w.writeframes(pcm)
    assert read(composite)[1]==pcm
    fast=ROOT/'narration/elevenlabs/complete-tempo1.15.wav'
    command=['ffmpeg','-y','-v','error','-i',str(composite),'-af','atempo=1.15','-ar','48000','-ac','1','-c:a','pcm_s16le',str(fast)]
    subprocess.run(command,check=True);fastn,fastpcm=read(fast)
    tempo={'speech_tempo_requested':1.15,'filter':'atempo=1.15','continuous_master_processing':True,'pitch_cents':0,'sample_rate':48000,'channels':1,'source':composite.relative_to(ROOT).as_posix(),'source_sha256':sha(composite.read_bytes()),'source_pcm_sha256':sha(pcm),'source_samples':cursor,'output':fast.relative_to(ROOT).as_posix(),'output_sha256':sha(fast.read_bytes()),'output_pcm_sha256':sha(fastpcm),'output_samples':fastn,'duration_ratio_measured':cursor/fastn,'raw_concat_exact':True,'source_sample_rate_unchanged':True,'only_time_processor':'atempo','pitch_or_asetrate_filter':False,'ffmpeg_version':subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0],'scope':'Two independently generated raw takes are concatenated as exact PCM. A single tempo-only pass transforms that continuous composite. PCM identity to the raw originals after tempo processing is not claimed.'}
    tempofile=ROOT/'narration/elevenlabs/complete-tempo-provenance.json';save(tempofile,tempo)
    identity={'authorization_sha256':sha(authfile.read_bytes()),'generation_mode':auth['generation_mode'],'voice_id':auth['voice_id'],'model_id':auth['model_id'],'tone_generation_id':auth['selected_generation_id'],'parts':[{k:r[k]for k in ['part_id','generation_id','master_sha256','master_pcm_sha256','prompt_sha256','cut_ids']}for r in rows]}
    descriptor={'generation_mode':auth['generation_mode'],'default_generation_policy':'single_take','two_part_exception_authorized':True,'voice_id':auth['voice_id'],'model_id':auth['model_id'],'speech_tempo':1.15,'pitch_cents':0,'authorization':{'path':authfile.relative_to(ROOT).as_posix(),'sha256':sha(authfile.read_bytes())},'parts':rows,'composite_master':{'path':composite.relative_to(ROOT).as_posix(),'sha256':sha(composite.read_bytes()),'pcm_sha256':sha(pcm),'samples':cursor},'fast_master':{'path':fast.relative_to(ROOT).as_posix(),'sha256':sha(fast.read_bytes()),'pcm_sha256':sha(fastpcm),'samples':fastn},'tempo_provenance':{'path':tempofile.relative_to(ROOT).as_posix(),'sha256':sha(tempofile.read_bytes())},'source_identity_payload':identity,'source_identity_sha256':sha(json.dumps(identity,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())}
    save(ROOT/'narration/two-part-sources.json',descriptor)
    print(json.dumps({'raw_seconds':cursor/48000,'fast_seconds':fastn/48000,'source_identity_sha256':descriptor['source_identity_sha256'],'actual_ratio':cursor/fastn},ensure_ascii=False))
if __name__=='__main__':main()
