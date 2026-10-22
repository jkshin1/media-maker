#!/usr/bin/env python3
"""Apply the user-authorized whole-project replacement at a verified quiet gap."""
from pathlib import Path
import hashlib,importlib.util,json,wave
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 with wave.open(str(p))as w:
  q=w.getparams();assert q.nchannels==1 and q.framerate==48000 and q.sampwidth==2
  return q,w.readframes(q.nframes)
def main():
 config=json.loads((ROOT/'narration/tasks-ko.json').read_text());assert config.get('authorized_task16_replacement') is True,'Explicit user authorization required.'
 base=ROOT/'narration/elevenlabs/attempt2-incomplete/take.wav';patch=ROOT/'narration/elevenlabs/task16-replacement/take.wav';q,pcm=read(base);qp,patchpcm=read(patch)
 report=json.loads((ROOT/'narration/elevenlabs/attempt2-incomplete/alignment-report.json').read_text());assert report['master_sha256']==sha(base)
 asr=json.loads((ROOT/'narration/transcription-v8-complete/take.json').read_text())
 spec=importlib.util.spec_from_file_location('align_v8',ROOT/'align-tasks-v8.py');align=importlib.util.module_from_spec(spec);spec.loader.exec_module(align)
 words=align.whisper_words(asr);quiet=align.quiet_regions(pcm,48000,2)
 left=next(c for c in report['cuts']if c['id']=='task14_cut5');right=next(c for c in report['cuts']if c['id']=='task16_cut1')
 point,boundary=align.safe_boundary(left['word_end'],right['word_start'],quiet,words)
 sample=round(point*48000);complete=pcm[:sample*2]+patchpcm
 target=ROOT/'narration/elevenlabs/take.wav'
 with wave.open(str(target),'wb')as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(complete)
 with wave.open(str(target))as w:assert w.readframes(w.getnframes())==complete
 proof={'generation_mode':'single_take_plus_user_authorized_whole_task16_replacement','user_authorized':True,'authorization':'2026-10-15 direct user approval to regenerate only all five lines of Kim Ji-eun task with the same Kyung voice.','voice_name':config['voice_name'],'voice_id':config['voice_id'],'master_sha256':sha(target),'sample_rate':48000,'channels':1,'samples':len(complete)//2,'duration':len(complete)/2/48000,'no_time_stretch':True,'no_spoken_word_crossfade':True,'word_safe_join':boundary,'sources':[{'file':str(base.relative_to(ROOT)),'sha256':sha(base),'start_sample':0,'end_sample':sample,'destination_start_sample':0},{'file':str(patch.relative_to(ROOT)),'sha256':sha(patch),'start_sample':0,'end_sample':qp.nframes,'destination_start_sample':sample}],'scope':'All first eleven project samples retained through their complete final sentence. The entire twelfth project is replaced; no syllable stitching or voice conversion.'}
 for name in ['master-composition-provenance.json','import-provenance.json']:(target.parent/name).write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'duration':proof['duration'],'master_sha256':proof['master_sha256'],'join_sample':sample,'join_seconds':sample/48000}))
if __name__=='__main__':main()
