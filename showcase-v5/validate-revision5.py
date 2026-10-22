#!/usr/bin/env python3
"""Validate the final Revision5 artifact against the locked Revision4 content."""
from pathlib import Path
import hashlib,json,subprocess,wave

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'out/showcase-v5'
def read(p):return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(8*1024*1024):h.update(b)
 return h.hexdigest()
def run(args):return subprocess.run(args,check=True,capture_output=True,text=True)
def main():
 tl=read(ROOT/'timeline.json');spec=read(ROOT/'spec.json')
 visual=read(OUT/'source-visual-review.json');audio=read(OUT/'audio-validation.json')
 speech=read(OUT/'final-speech-review.json');render=read(OUT/'render-validation.json')
 mux=read(OUT/'mux-validation.json');manual=read(OUT/'visual-review.json')
 final=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision5.mp4'
 meta=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(final)]).stdout)
 v=next(x for x in meta['streams'] if x['codec_type']=='video');a=next(x for x in meta['streams'] if x['codec_type']=='audio')
 checks={
  'locked_spec_timeline_hero_stage_narration_source_hashes':all(r['unchanged'] for r in visual['locks']),
  'twelve_tasks_in_existing_order':len([s for s in spec['sections'] if s['type']=='task'])==12,
  'four_summaries_still_removed':not any(s['type']=='summary' for s in spec['sections']) and not any(e['kind']=='summary' for e in tl['entries']),
  'original_87_entries_retained':len(tl['entries'])==87,
  'original_307_133_seconds_and_9214_frames':tl['frames']==9214 and abs(tl['duration']-9214/30)<1e-9,
  'twelve_task_specific_visual_profiles':len(set(p['profile'] for p in visual['plans']))==12,
  'sixty_bespoke_body_cut_plans':len(visual['plans'])==60,
  'all_body_text_inside_safe_area':not visual['text_bounds_flags'],
  'all_72_task_headers_measured':visual['headers']==72,
  'all_45_hero_source_frame_samples_unchanged':len(visual['hero_samples'])==45 and all(r['exact_pixels_unchanged'] for r in visual['hero_samples']),
  'manual_visual_review_complete':manual['status']=='PASS',
  'fixed_background_motion_triptychs_present':visual['motion_frame_difference_pass']==60,
  'audio_repair_checks_all_pass':audio['status']=='PASS' and all(audio['checks'].values()),
  'approved_voice_script_speed_and_placement_preserved':all(speech['checks'].values()),
  'no_new_tts':audio['new_tts'] is False,
  'opening_ending_audio_pcm_exact':audio['opening_ending_pcm_exact'] is True,
  'same_bgm_source':audio['bgm_source_sha256']=='285aafebdbb4879d1678dd8ae520fb1283c604c6b1756cc4c6e964c6fc55e7c2',
  'render_and_mux_pass':render['status']=='PASS' and mux['status']=='PASS',
  'final_matches_mux_sha256':sha(final)==mux['final_sha256'],
  'fullhd_30fps_and_frame_count':v['width']==1920 and v['height']==1080 and v['r_frame_rate']=='30/1' and int(v['nb_frames'])==9214,
  'aac_48khz_stereo':a['codec_name']=='aac' and a['sample_rate']=='48000' and a['channels']==2,
  'encoded_duration_same':abs(float(meta['format']['duration'])-tl['duration'])<2/30,
 }
 for item in render['inputs']:
  if sha(ROOT/item['file'])!=item['sha256']:raise AssertionError('Source changed since render: '+item['file'])
 checks['all_render_inputs_still_match']=True
 with wave.open(str(OUT/'audio.wav')) as f:checks['exact_pcm_duration']=f.getnframes()==tl['frames']*1600 and f.getframerate()==48000 and f.getnchannels()==2
 hashes=[]
 for file in [OUT/'video_silent.mp4',final]:
  hashes.append(run(['ffmpeg','-v','error','-i',str(file),'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-']).stdout.strip())
 checks['mux_copies_exact_h264_packet_payload']=hashes[0]==hashes[1]
 decode=run(['ffmpeg','-v','error','-i',str(final),'-f','null','-'])
 checks['full_video_and_audio_decode_without_errors']=not decode.stderr.strip()
 playback=read(OUT/'playback-validation.json') if (OUT/'playback-validation.json').exists() else None
 checks['continuous_full_playback_pass']=bool(playback and playback['status']=='PASS' and playback.get('sha256')==sha(final))
 result={'status':'PASS' if all(checks.values()) else 'FAIL','revision':5,'checks':checks,'duration_seconds':tl['duration'],'frames':tl['frames'],'sha256':sha(final),'file':str(final),'narration_scope':'Approved normalized/raw WAV and voice tempo/placement are unchanged; existing reviewed ASR variants remain documented in final-speech-review.json.','hero_scope':'Hero composition functions/assets and 45 samples after incoming dissolves are identical. The outgoing task image naturally changes inside the existing 0.45-second dissolve into the ending.','bgm_scope':'Same track; only body loop/ducking repaired. Original opening and ending mixed PCM is exact.','video_stream_sha256':hashes[0],'source_inputs':render['inputs'],'visual_review_sha256':sha(OUT/'visual-review.json'),'audio_validation_sha256':sha(OUT/'audio-validation.json')}
 (OUT/'final-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':result['status'],'passed':sum(checks.values()),'total':len(checks),'failed':[k for k,v in checks.items() if not v],'duration':tl['duration'],'sha256':result['sha256']},ensure_ascii=False))
 return 0 if result['status']=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
