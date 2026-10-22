#!/usr/bin/env python3
"""Final media validation for the twelve first-photo overlay removals."""
from pathlib import Path
import hashlib,json,subprocess
from audio import audio_hash
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'out/showcase-v6'
def load(p):return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(8*1024*1024):h.update(b)
 return h.hexdigest()
def run(args):return subprocess.run(args,check=True,capture_output=True,text=True)
def main():
 tl=load(ROOT/'timeline.json');scope=load(OUT/'overlay-removal-validation.json')
 audio=load(OUT/'audio-validation.json');mux=load(OUT/'mux-validation.json')
 render=load(OUT/'render-validation.json');visual=load(OUT/'visual-review.json')
 encoded=load(OUT/'encoded-visual-review.json');playback=load(OUT/'playback-validation.json')
 final=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision6.mp4'
 meta=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(final)]).stdout)
 video=next(x for x in meta['streams'] if x['codec_type']=='video')
 voice=next(x for x in meta['streams'] if x['codec_type']=='audio')
 checks={
  'only_requested_first_photo_overlay_change':scope['status']=='PASS' and all(c['pass'] for c in scope['checks'].values()),
  'scope_review_source_hashes_current':all(sha(ROOT/f)==v for f,v in scope['source_hashes'].items()),
  'manual_first_photo_review_pass':visual['status']=='PASS',
  'decoded_final_frame_review_pass':encoded['status']=='PASS' and encoded['video_sha256']==sha(final),
  'locked_duration_and_frames':tl['frames']==9214 and abs(tl['duration']-9214/30)<1e-9,
  'fullhd_30fps_9214frames':video['width']==1920 and video['height']==1080 and video['r_frame_rate']=='30/1' and int(video['nb_frames'])==9214,
  'final_duration_unchanged':abs(float(meta['format']['duration'])-tl['duration'])<2/30,
  'aac_48000_stereo':voice['codec_name']=='aac' and voice['sample_rate']=='48000' and voice['channels']==2,
  'audio_source_validation_pass':audio['status']=='PASS' and all(audio['checks'].values()),
  'complete_approved_aac_packets_preserved':audio_hash(final)==audio['aac_packet_payload_hash'],
  'complete_approved_decoded_pcm_preserved':audio_hash(final,True)==audio['decoded_48000_stereo_s16le_hash'],
  'no_audio_reencoding_or_new_tts':mux['audio_reencoded'] is False and mux['new_tts'] is False,
  'render_and_mux_pass':render['status']==mux['status']=='PASS',
  'final_sha256_matches_mux':sha(final)==mux['final_sha256'],
  'all_render_input_hashes_still_match':all(sha(ROOT/r['file'])==r['sha256'] for r in render['inputs']),
  'continuous_playback_complete':playback['status']=='PASS' and playback['sha256']==sha(final),
 }
 hashes=[run(['ffmpeg','-v','error','-i',str(p),'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-']).stdout.strip() for p in [OUT/'video_silent.mp4',final]]
 checks['video_packet_payload_copied_exactly']=hashes[0]==hashes[1]
 decode=run(['ffmpeg','-v','error','-i',str(final),'-f','null','-'])
 checks['full_video_audio_decode_no_errors']=not decode.stderr.strip()
 report={'status':'PASS' if all(checks.values()) else 'FAIL','revision':6,'checks':checks,'file':str(final),'sha256':sha(final),'duration_seconds':tl['duration'],'frames':tl['frames'],'visual_scope':'Twelve first-photo cuts lose decorative rings/crosshairs/cursors/guides; the existing camera drift, photographs and headers remain. Their outgoing 0.45-second dissolves naturally reflect the removal. Other scene logic is unchanged; 225 native sample frames are RGBA-identical.','audio_scope':'Complete approved Revision5 AAC packets and decoded PCM are identical. No narration/BGM mixing, speed change or encoding.','continuous_playback_scope':'Muted 1x continuous browser playback is separate from the exact audio stream validation.','input_hashes':render['inputs'],'scope_review_sha256':sha(OUT/'overlay-removal-validation.json'),'audio_validation_sha256':sha(OUT/'audio-validation.json'),'video_packet_payload_hash':hashes[0]}
 (OUT/'final-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':report['status'],'passed':sum(checks.values()),'total':len(checks),'failed':[k for k,v in checks.items() if not v],'duration':tl['duration'],'sha256':report['sha256']}))
 return 0 if all(checks.values()) else 2
if __name__=='__main__':raise SystemExit(main())
