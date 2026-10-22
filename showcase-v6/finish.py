#!/usr/bin/env python3
"""Copy the new video and the complete approved AAC into Revision6."""
from pathlib import Path
import hashlib,json,subprocess
from audio import audio_hash
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parent/'out/showcase-v6'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 tl=json.loads((ROOT/'timeline.json').read_text());render=json.loads((OUT/'render-validation.json').read_text());audio=json.loads((OUT/'audio-validation.json').read_text())
 assert render['status']==audio['status']=='PASS'
 for item in render['inputs']:assert sha(ROOT/item['file'])==item['sha256'],item['file']
 silent=OUT/'video_silent.mp4';music=ROOT/audio['source_audio_file']
 assert sha(silent)==render['sha256'] and sha(music)==audio['approved_aac_file_sha256']
 final=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision6.mp4'
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(silent),'-i',str(music),'-map','0:v:0','-map','1:a:0','-c','copy','-movflags','+faststart',str(final)],check=True)
 packet_equal=audio_hash(final)==audio['aac_packet_payload_hash'];pcm_equal=audio_hash(final,True)==audio['decoded_48000_stereo_s16le_hash']
 assert packet_equal and pcm_equal
 report={'status':'PASS','method':'New visual stream plus exact approved Revision5 AAC; both streams copied.','duration_seconds':tl['duration'],'frames':tl['frames'],'silent_video_sha256':sha(silent),'final_sha256':sha(final),'audio_stream_copied':True,'video_stream_copied':True,'audio_reencoded':False,'new_tts':False,'aac_packet_payload_identical_to_revision5':packet_equal,'decoded_audio_pcm_identical_to_revision5':pcm_equal,'aac_packet_payload_hash':audio['aac_packet_payload_hash'],'decoded_48000_stereo_s16le_hash':audio['decoded_48000_stereo_s16le_hash']}
 (OUT/'mux-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'file':str(final.resolve()),**report}))
if __name__=='__main__':main()
