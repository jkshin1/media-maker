#!/usr/bin/env python3
"""Mux the diversified task visuals with the protected narration and repaired BGM."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;OUT=HERE.parent/'out/showcase-v5'
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 tl=json.loads((HERE/'timeline.json').read_text());render=json.loads((OUT/'render-validation.json').read_text())
 assert render['status']=='PASS'
 for item in render['inputs']:assert sha(HERE/item['file'])==item['sha256'],item['file']
 silent=OUT/'video_silent.mp4';audio=OUT/'audio.wav';assert sha(silent)==render['sha256']
 assert json.loads((OUT/'audio-validation.json').read_text())['status']=='PASS'
 meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(audio)]))
 stream=meta['streams'][0];assert int(stream['sample_rate'])==48000 and stream['channels']==2
 assert abs(float(meta['format']['duration'])-tl['duration'])<1/48000+1e-6
 final=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision5.mp4'
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(silent),'-i',str(audio),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart',str(final)],check=True)
 report={'status':'PASS','method':'Task-specific visuals on the unchanged timeline, with approved narration and repaired body BGM; video stream copied and audio encoded once to AAC.','duration_seconds':tl['duration'],'frames':tl['frames'],'silent_video_sha256':sha(silent),'audio_pcm_sha256':sha(audio),'final_sha256':sha(final),'audio_reencoded':True,'new_tts':False,'video_stream_copied':True}
 (OUT/'mux-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'file':str(final),**report}))
if __name__=='__main__':main()
