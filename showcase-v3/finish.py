#!/usr/bin/env python3
"""Mux the new visual render with the approved audio stream without re-encoding."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
OUT=HERE.parent/'out/showcase-v3'
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 tl=json.loads((HERE/'timeline.json').read_text())
 render=json.loads((OUT/'render-validation.json').read_text())
 assert render['status']=='PASS'
 for record in render['inputs']:
  assert sha(HERE/record['file'])==record['sha256'],record['file']
 silent=OUT/'video_silent.mp4';audio=HERE/'narration/approved-mix.m4a'
 assert sha(silent)==render['sha256']
 provenance=json.loads((HERE/'narration/approved-mix-provenance.json').read_text())
 assert sha(audio)==provenance['sha256']
 final=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision3.mp4'
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(silent),'-i',str(audio),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','copy','-movflags','+faststart',str(final)],check=True)
 report={'status':'PASS','method':'Native scene score mask follows the card down 107.5px before the unchanged dissolve; approved AAC is copied without processing.','duration_seconds':tl['duration'],'frames':tl['frames'],'silent_video_sha256':sha(silent),'approved_audio_sha256':sha(audio),'final_sha256':sha(final),'audio_reencoded':False,'timeline_edited':False}
 (OUT/'mux-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'file':str(final),**report}))
if __name__=='__main__':main()
