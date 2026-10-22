#!/usr/bin/env python3
"""Copy the locked visual stream and encode the natural Kyung mix once."""
from pathlib import Path
import hashlib,json,subprocess

ROOT=Path(__file__).resolve().parent;OUT=ROOT.parent/'out/showcase-v11'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def streamhash(p):return subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-'],text=True).strip()
def main():
    audio=load(OUT/'audio-validation.json');baseline=load(ROOT/'baseline-provenance.json');auth=load(ROOT/'authorization.json');timeline=load(ROOT/'timeline.json')
    assert audio['status']=='PASS'and all(audio['checks'].values())and audio['pitch_cents']==0 and audio['speech_tempo']==1
    assert auth['pitch_or_time_processor_allowed']is False and auth['pitch_shift_cents']==0
    for name,h in audio['input_bindings'].items():assert sha(ROOT/name)==h,name
    for name,d in audio['files'].items():assert sha(OUT/name)==d['sha256'],name
    silent=ROOT/baseline['locked_silent_file'];mix=OUT/'audio.wav';video=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision11.mp4'
    assert sha(silent)==baseline['locked_silent_sha256']and sha(ROOT/'timeline.json')==baseline['timeline_sha256']
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(silent),'-i',str(mix),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','256k','-ar','48000','-ac','2','-movflags','+faststart',str(video)],check=True)
    meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]));v=next(s for s in meta['streams']if s['codec_type']=='video');a=next(s for s in meta['streams']if s['codec_type']=='audio')
    original_visual=load(ROOT/'baseline-reviews/encoded-visual-review.json');stream=streamhash(video)
    checks={'video_packets_exact_locked_baseline':stream==streamhash(silent)==original_visual['video_stream_sha256'],
        'frames9450':int(v['nb_frames'])==9450,'fullHD30fps':(v['width'],v['height'],v['r_frame_rate'])==(1920,1080,'30/1'),
        'exact315s':abs(float(meta['format']['duration'])-315)<.001,'AAC48k_stereo':(a['codec_name'],a['sample_rate'],a['channels'])==('aac','48000',2),
        'audio_clock315s':abs(float(a['duration'])-315)<.001,'unchanged_timeline':sha(ROOT/'timeline.json')==baseline['timeline_sha256']}
    subprocess.run(['ffmpeg','-v','error','-xerror','-err_detect','explode','-i',str(video),'-map','0:v:0','-map','0:a:0','-f','null','-'],check=True,capture_output=True);checks['whole_AV_strict_decode']=True
    assert all(checks.values()),checks
    report={'revision':11,'status':'PASS','final_video':video.name,'final_sha256':sha(video),'final_video_sha256':sha(video),'video_stream_sha256':stream,
        'locked_silent_sha256':sha(silent),'pcm_mix_sha256':sha(mix),'narration_sha256':sha(OUT/'narration.wav'),'timeline_sha256':sha(ROOT/'timeline.json'),
        'source_identity_sha256':audio['source_identity_sha256'],'duration_seconds':315,'frames':9450,'speech_tempo':1,'pitch_cents':0,
        'checks':checks,'checks_passed':sum(checks.values()),'checks_total':len(checks),'audio_validation_sha256':sha(OUT/'audio-validation.json'),
        'input_bindings':{'finish.py':sha(ROOT/'finish.py'),'assets/video/locked-silent.mp4':sha(silent),'timeline.json':sha(ROOT/'timeline.json'),'audio-processing-manifest.json':sha(ROOT/'audio-processing-manifest.json')},
        'method':'Exact locked video packets copied; natural original Kyung PCM at unchanged clock plus unchanged BGM encoded once to AAC256k. Complete AV strict decoding performed.'}
    save(OUT/'mux-validation.json',report)
    oldplay=load(ROOT/'baseline-reviews/playback-validation.json')
    visual_checks={'exact_video_packet_identity':checks['video_packets_exact_locked_baseline'],'same_entire315s_clock':checks['exact315s']and checks['frames9450'],
        'baseline_full1x_playback_complete':oldplay['status']=='PASS'and oldplay['actual']['ended']and oldplay['actual']['rate']==1 and oldplay['sha256']==oldplay['sha256_after_playback']==baseline['baseline_final_video_sha256'],
        'no_video_reencode_or_visual_edit':True,'whole_current_AV_decode':True}
    save(OUT/'visual-preservation-validation.json',{'revision':11,'status':'PASS','final_video_sha256':sha(video),'video_stream_sha256':stream,'locked_silent_sha256':sha(silent),'timeline_sha256':sha(ROOT/'timeline.json'),
        'baseline_visual_review_sha256':sha(ROOT/'baseline-reviews/encoded-visual-review.json'),'baseline_full_playback_sha256':sha(ROOT/'baseline-reviews/playback-validation.json'),'mux_validation_sha256':sha(OUT/'mux-validation.json'),
        'scope':'Exact immutable video packet identity reuses the existing complete1x315s visual-playback evidence. No new visual rendering or browser replay; current complete AV decoding checked separately.',
        'new_full_browser_playback_performed':False,'human_listening_acceptance_claimed':False,'checks':visual_checks,'checks_passed':sum(visual_checks.values()),'checks_total':len(visual_checks)})
    print(json.dumps({'status':'PASS','video':str(video),'sha256':sha(video),'frames':9450,'duration':315,'video_packets_preserved':True}))
if __name__=='__main__':main()
