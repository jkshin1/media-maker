#!/usr/bin/env python3
"""Mask legacy renders as needed, then mux verified audio by video copy."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;OUT=HERE.parent/'out/showcase'
def run(a):subprocess.run(a,check=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 tl=json.loads((HERE/'timeline.json').read_text());silent=OUT/'video_silent.mp4';mask=HERE/'score-redaction.json'
 render=json.loads((OUT/'render-validation.json').read_text())
 stage_text=(HERE/'stage.mjs').read_text()
 native_mask=any(i['file']=='stage.mjs' and i['sha256']==sha(HERE/'stage.mjs') for i in render['inputs']) and 'fillRect(1572+' in stage_text
 if mask.exists() and not native_mask:
  data=json.loads(mask.read_text());original=OUT/'video_silent.native.mp4'
  if not original.exists():silent.rename(original)
  assert len(data['boxes'])==1
  b=data['boxes'][0];q=f"pow(1-clip((t-{b['entrance_start']})/{b['entrance_duration']},0,1),3)"
  graph=f"[0:v][1:v]overlay=x='{b['x']}+{b['dx']}*{q}':y='{b['y']}+{b['dy']}*{q}':enable='between(t,{b['entrance_start']-0.00001},{b['end']})':shortest=1,format=yuv420p[v]"
  run(['ffmpeg','-y','-v','error','-i',str(original),'-f','lavfi','-i',f"color=c=0x14212A:s={b['w']}x{b['h']}:r=30:d={tl['duration']}",'-filter_complex',graph,'-map','[v]','-an','-frames:v',str(tl['frames']),'-c:v','libx264','-preset','fast','-crf','16','-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-movflags','+faststart',str(silent)])
  report={**data,'status':'PASS','native_video_sha256':sha(original),'patched_video_sha256':sha(silent),'method':'Hide provided storyboard example-score columns; no numeric values were invented or replaced.'}
  (OUT/'score-redaction-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 elif mask.exists():
  report={**json.loads(mask.read_text()),'status':'PASS','native_video_sha256':sha(silent),'method':'Score masking is included inside the native scene renderer before the 0.45-second dissolve.'}
  (OUT/'score-redaction-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 final=OUT/'RD_Process_AI_Fast_Track_Showcase.mp4'
 run(['ffmpeg','-y','-v','error','-i',str(silent),'-i',str(OUT/'audio.wav'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-t',str(tl['duration']),'-movflags','+faststart',str(final)])
 print('Final MP4',final)
if __name__=='__main__':main()
