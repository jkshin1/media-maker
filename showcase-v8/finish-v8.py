#!/usr/bin/env python3
"""Mux the verified Revision8 video with its newly verified PCM mix."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parent/'out/showcase-v8'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def streamhash(p,kind):return subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-map',f'0:{kind}:0','-c','copy','-f','hash','-hash','sha256','-'],text=True).strip()
def main():
 tl=json.loads((ROOT/'timeline.json').read_text());render=json.loads((OUT/'render-validation.json').read_text());audio=json.loads((OUT/'audio-validation.json').read_text())
 assert tl.get('revision')==8 and not tl.get('preview_only')
 assert render['status']==audio['status']=='PASS' and not render.get('preview_only')
 for item in render['inputs']:assert sha(ROOT/item['file'])==item['sha256'],item['file']
 for item in audio['input_bindings']:assert sha(ROOT/item['file'])==item['sha256'],item['file']
 silent=OUT/'video_silent.mp4';music=OUT/'audio.wav';assert sha(silent)==render['sha256'] and sha(music)==audio['audio_sha256']
 final=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision8.mp4'
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(silent),'-i',str(music),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-movflags','+faststart',str(final)],check=True)
 meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(final)]));v=next(s for s in meta['streams']if s['codec_type']=='video');a=next(s for s in meta['streams']if s['codec_type']=='audio')
 checks={'video_stream_copied':streamhash(final,'v')==streamhash(silent,'v'),'frames_match':int(v['nb_frames'])==tl['frames'],'dimensions_1920_1080':v['width']==1920 and v['height']==1080,'fps30':v['r_frame_rate']=='30/1','aac_48000_stereo':a['codec_name']=='aac' and a['sample_rate']=='48000' and a['channels']==2,'duration_matches':abs(float(meta['format']['duration'])-tl['duration'])<2/30}
 subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(final),'-f','null','-'],check=True);checks['full_audio_video_decode']=True
 report={'status':'PASS'if all(checks.values())else'FAIL','revision':8,'checks':checks,'duration_seconds':tl['duration'],'frames':tl['frames'],'final_sha256':sha(final),'silent_video_sha256':sha(silent),'pcm_mix_sha256':sha(music),'method':'Verified new silent video stream copied; newly prepared PCM audio encoded once to AAC. Approved opening and ending are PCM-identical before this AAC encode.','audio_reencoded':True,'new_task_tts':True,'outer_pcm_identical_before_aac':True,'outer_aac_packet_identity_claimed':False}
 (OUT/'mux-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'file':str(final),**report}));assert all(checks.values())
if __name__=='__main__':main()
