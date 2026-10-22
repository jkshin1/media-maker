#!/usr/bin/env python3
"""Gate current Revision10 receipts, copy verified video and encode AAC256k."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import wave

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'out/showcase-v10'
PLAN_SHA='ff38348f4f94a046381dfc29d357e8a6ebfb14224d4ab011e1706725cbda7abf'
SOURCE_ID='92c31c5917cbb6a5c7d8f7f998ac005bdd43bfb1e69e79183333c5dfcca5e3c2'
PRE_RECEIPTS=['render-validation.json','visual-validation.json','retime-native-visual-review.json',
              'silent-encoded-visual-review.json','raw-placement-validation.json',
              'raw-placement-independent-review.json','completeness-review.json',
              'dsp-validation.json','audio-validation.json','independent-audio-validation.json',
              'final-speech-validation.json']
_HASHES={}

def load(path): return json.loads(Path(path).read_text())

def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

def sha(path):
    path=Path(path);st=path.stat();key=(str(path.resolve()),st.st_size,st.st_mtime_ns)
    if key not in _HASHES:
        h=hashlib.sha256()
        with path.open('rb') as f:
            for block in iter(lambda:f.read(1048576),b''): h.update(block)
        _HASHES[key]=h.hexdigest()
    return _HASHES[key]

def locate(name,root=ROOT,out=OUT):
    p=Path(name)
    if p.is_absolute():
        parts=p.parts
        # A frozen review may record its original workspace path. Resolve only
        # these exact Revision10 anchors into the current clone, even when the
        # old absolute path still exists; never fall back to that old file.
        for anchor,base in [(('out','showcase-v10'),out),(('showcase-v10',),root)]:
            for i in range(len(parts)-len(anchor)+1):
                if tuple(parts[i:i+len(anchor)])==anchor:
                    suffix=parts[i+len(anchor):]
                    if '..' in suffix: raise ValueError('Receipt path escapes its canonical Revision10 root.')
                    candidate=base.joinpath(*suffix)
                    if not candidate.resolve().is_relative_to(base.resolve()): raise ValueError('Receipt path escapes its canonical Revision10 root.')
                    return candidate
        return p
    if p.parts and (p.parts[0]=='out' or p.parts[0].startswith('showcase-v')): return root.parent/p
    candidate=root/p
    return candidate if candidate.exists() else out/p if (out/p).exists() else candidate

def binding_rows(report):
    rows=[]
    for field in ['inputs','input_bindings','source_hashes']:
        value=report.get(field,{})
        if isinstance(value,dict): rows.extend({'file':k,'sha256':v} for k,v in value.items() if isinstance(v,str))
        elif isinstance(value,list):
            rows.extend({'file':r.get('file',r.get('path')),'sha256':r.get('sha256')} for r in value if isinstance(r,dict))
    return [r for r in rows if r['file'] and r['sha256']]

def receipt_good(report):
    if not str(report.get('status','')).startswith('PASS'): return False
    checks=report.get('checks',{})
    for value in checks.values() if isinstance(checks,dict) else checks:
        if value is False or isinstance(value,dict) and value.get('pass') is False: return False
    return True

def has_hash(report,expected,keys): return bool(expected) and any(report.get(k)==expected for k in keys)

def asr_binding(report,root=ROOT,out=OUT):
    value=next((report[k] for k in ['asr','ASR','asr_path','ASR_path','asr_file','ASR_file'] if report.get(k)),None)
    expected=next((report[k] for k in ['asr_sha256','ASR_sha256','transcript_sha256'] if report.get(k)),None)
    if isinstance(value,dict):
        expected=expected or value.get('sha256');value=value.get('path',value.get('file'))
    if not isinstance(value,str) or not expected: return False,{'error':'Fresh processed ASR path/SHA missing.'}
    path=locate(value,root,out)
    return path.is_file() and sha(path)==expected,{'file':str(path),'expected_sha256':expected}

def preflight(root=ROOT,out=OUT,require_final_speech=True):
    checks={};receipts={};missing=[]
    def add(name,passed,details=None): checks[name]={'pass':bool(passed),'details':details}
    for name in PRE_RECEIPTS:
        if name=='final-speech-validation.json' and not require_final_speech:
            path=out/name
            add('no_existing_processed_speech_FAILURE',not path.exists() or load(path).get('status')!='FAIL')
            continue
        path=out/name
        if not path.is_file():missing.append(name);add('receipt_'+name,False,'MISSING_EVIDENCE');continue
        try: receipts[name]=load(path);add('receipt_'+name,receipt_good(receipts[name]),receipts[name].get('status'))
        except (ValueError,OSError) as exc:add('receipt_'+name,False,str(exc))
    try:
        tl=load(root/'timeline.json');auth=load(root/'narration/retime-tone-authorization.json');plan=load(root/'narration/retime/approved-plan.json');manifest=load(root/'narration/placement-manifest.json')
    except (ValueError,OSError) as exc:
        add('current_source_configuration',False,str(exc));return checks,receipts,missing,None
    timeline_sha=sha(root/'timeline.json');manifest_sha=sha(root/'narration/placement-manifest.json')
    entries=tl.get('entries',[]);spoken=[e for e in entries if e.get('kind')=='cut']
    add('approved_actual315s_9450frames',tl.get('revision')==10 and not tl.get('preview_only') and (tl.get('fps'),tl.get('frames'),tl.get('duration'))==(30,9450,315))
    add('68_spoken_69_entries_14_sections',len(spoken)==68 and len(entries)==69 and len(tl.get('sections',[]))==14)
    add('frame_clock_contiguous',bool(entries) and entries[0]['start_frame']==0 and entries[-1]['end_frame']==9450 and all(a['end_frame']==b['start_frame'] for a,b in zip(entries,entries[1:])))
    add('four_second_last_card',bool(entries) and entries[-1].get('kind')=='silent' and (entries[-1]['start_frame'],entries[-1]['end_frame'])==(9330,9450))
    fields=['section_id','kind','cut_id','cut_index','start_frame','end_frame','caption']
    add('exact_approved_visual_clock',[[e.get(k) for k in fields] for e in entries]==[[e.get(k) for k in fields] for e in plan['entries']])
    add('direct_user_retime_and_pitch_authorization',auth.get('authorization_source')=='direct_user_reply_in_current_chat' and auth.get('approved_proposal_sha256')==PLAN_SHA==sha(root/'narration/retime/approved-plan.json') and (auth.get('speech_tempo'),auth.get('pitch_cents'),auth.get('duration_seconds'))==(1,315,315))
    add('same_two_current_sources',tl.get('source_identity_sha256')==manifest.get('source_identity_sha256')==auth.get('source_identity_sha256')==SOURCE_ID)
    add('tempo1_no_spoken_sample_removal',tl.get('speech_tempo')==1 and manifest.get('spoken_samples_removed')==0 and manifest.get('piece_count')==77)
    mismatches=[];count=0
    for name,report in receipts.items():
        for row in binding_rows(report):
            path=locate(row['file'],root,out);count+=1
            if not path.is_file() or sha(path)!=row['sha256']:mismatches.append({'receipt':name,'file':row['file']})
    add('all_current_receipt_input_bindings',not mismatches,{'count':count,'mismatches':mismatches})
    for name in ['visual-validation.json','retime-native-visual-review.json','silent-encoded-visual-review.json']:
        report=receipts.get(name,{})
        bound=report.get('timeline_sha256')==timeline_sha or any(r['file']=='timeline.json' and r['sha256']==timeline_sha for r in binding_rows(report))
        add('current_timeline_'+name,bound)
    silent=out/'video_silent.mp4';render=receipts.get('render-validation.json',{})
    add('render315_and_current_silent_video',silent.is_file() and render.get('duration')==315 and render.get('frames')==9450 and render.get('sha256')==sha(silent))
    encoded=receipts.get('silent-encoded-visual-review.json',{})
    add('silent_encoded_visual_review_current',silent.is_file() and has_hash(encoded,sha(silent),['video_sha256','sha256','file_sha256']))
    expected_channels={'narration-raw.wav':1,'narration.wav':1,'bgm-loop.wav':2,'audio.wav':2};file_hashes={};wav_errors=[]
    audio=receipts.get('audio-validation.json',{})
    for name,channels in expected_channels.items():
        path=out/name
        try:
            with wave.open(str(path)) as w: assert (w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getnframes())==(48000,channels,2,15120000)
            file_hashes[name]=sha(path)
            assert audio.get('files',{}).get(name,{}).get('sha256')==file_hashes[name]
        except (OSError,AssertionError,wave.Error) as exc:wav_errors.append({'file':name,'error':str(exc)})
    add('four_current315s_48k_PCM_files',not wav_errors,{'errors':wav_errors})
    add('audio_current_timeline_and_placement',audio.get('timeline_sha256')==timeline_sha and audio.get('placement_manifest_sha256')==manifest_sha and audio.get('audio_sha256')==file_hashes.get('audio.wav') and audio.get('speech_tempo')==1 and audio.get('pitch_cents')==315)
    raw=receipts.get('raw-placement-validation.json',{});independent_raw=receipts.get('raw-placement-independent-review.json',{})
    add('raw77piece_current_source_proof',raw.get('timeline_sha256')==timeline_sha and raw.get('source_identity_sha256')==SOURCE_ID and raw.get('piece_count')==77 and raw.get('raw_output',{}).get('sha256')==file_hashes.get('narration-raw.wav'))
    add('independent_raw_current_placement',independent_raw.get('timeline_sha256')==timeline_sha and independent_raw.get('placement_manifest_sha256')==manifest_sha and independent_raw.get('source_identity_sha256')==SOURCE_ID and independent_raw.get('sentences_complete')==68)
    complete=receipts.get('completeness-review.json',{})
    add('current_pair68_complete',complete.get('source_identity_sha256')==SOURCE_ID and complete.get('sentences_complete')==68)
    dsp=receipts.get('dsp-validation.json',{})
    add('DSP_current_raw_authorization_and_rate',dsp.get('source_raw_sha256')==file_hashes.get('narration-raw.wav') and dsp.get('authorization_sha256')==sha(root/'narration/retime-tone-authorization.json') and dsp.get('pitch_cents')==315 and dsp.get('speech_tempo')==1 and dsp.get('aligned_samples')==15120000)
    for key,name in [('engine_receipt_sha256','pitch-engine.json'),('untrimmed_sha256','narration-pitch-untrimmed.wav'),('aligned_float_sha256','narration-pitch-aligned.wav')]:
        path=out/'audio-audit'/name;add('DSP_output_'+name,path.is_file() and dsp.get(key)==sha(path))
    independent_audio=receipts.get('independent-audio-validation.json',{})
    add('independent_audio_current4WAV',independent_audio.get('audio_sha256')==file_hashes.get('audio.wav') and independent_audio.get('narration_sha256')==file_hashes.get('narration.wav') and independent_audio.get('bgm_sha256')==file_hashes.get('bgm-loop.wav') and independent_audio.get('raw_sha256')==file_hashes.get('narration-raw.wav') and independent_audio.get('timeline_sha256')==timeline_sha)
    if require_final_speech:
        speech=receipts.get('final-speech-validation.json',{})
        add('current_processed_voice68_review',has_hash(speech,file_hashes.get('narration.wav'),['narration_sha256','voice_sha256']) and speech.get('timeline_sha256')==timeline_sha and speech.get('source_identity_sha256')==SOURCE_ID and speech.get('sentences_complete',speech.get('spoken_lines_present'))==68)
        valid_asr,details=asr_binding(speech,root,out);add('fresh_processed_ASR_file_bound',valid_asr,details)
    return checks,receipts,missing,tl

def streamhash(path):
    return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-'],text=True).strip()

def strict_decode(path):
    subprocess.run(['ffmpeg','-v','error','-xerror','-err_detect','explode','-i',str(path),'-map','0:v:0','-map','0:a:0','-f','null','-'],check=True,capture_output=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check-only',action='store_true');parser.add_argument('--validate-existing',action='store_true',help='Rebind current passed reviews and verify the existing MP4 without rewriting it.');parser.add_argument('--allow-pending-final-speech',action='store_true',help='Create only a technical mux while final processed speech review is pending; final validation still requires it.');args=parser.parse_args()
    checks,receipts,missing,tl=preflight(require_final_speech=not args.allow_pending_final_speech);ready=all(c['pass'] for c in checks.values())
    readiness={'revision':10,'status':'PASS_READY_FOR_TECHNICAL_MUX' if ready else 'PENDING' if missing else 'FAIL','final_speech_review_deferred':args.allow_pending_final_speech,'production_complete':False,'missing_receipts':missing,'checks':checks,'checks_passed':sum(c['pass'] for c in checks.values()),'checks_total':len(checks),'video_created_by_this_check':False}
    save(OUT/'finish-readiness.json',readiness)
    if args.check_only or not ready:
        print(json.dumps({'status':readiness['status'],'missing':missing,'failed':[k for k,v in checks.items() if not v['pass']]}));raise SystemExit(0 if ready else 2)
    silent=OUT/'video_silent.mp4';audio=OUT/'audio.wav';final=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision10.mp4'
    source_video_hash=sha(silent);audio_hash=sha(audio)
    command=['ffmpeg','-y','-v','error','-i',str(silent),'-i',str(audio),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','256k','-ar','48000','-ac','2','-movflags','+faststart',str(final)]
    existing=None
    if args.validate_existing:
        existing=load(OUT/'mux-validation.json')
        assert final.is_file() and sha(final)==existing['final_sha256']
        assert existing['silent_video_sha256']==source_video_hash and existing['pcm_mix_sha256']==audio_hash
        assert existing['checks'].get('whole_AV_strict_decode') is True, 'The unchanged artifact needs a prior complete strict decode.'
    else:subprocess.run(command,check=True)
    meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(final)]))
    video=next(s for s in meta['streams'] if s['codec_type']=='video');encoded=next(s for s in meta['streams'] if s['codec_type']=='audio')
    result_checks={'video_stream_copied':streamhash(final)==streamhash(silent),'frames9450':int(video.get('nb_frames',0))==9450,'fullHD30fps':(video.get('width'),video.get('height'),video.get('r_frame_rate'))==(1920,1080,'30/1'),'AAC48k_stereo':(encoded.get('codec_name'),encoded.get('sample_rate'),encoded.get('channels'))==('aac','48000',2),'exact315s_container':abs(float(meta['format']['duration'])-315)<.001,'hard_max315':float(meta['format']['duration'])<=315.001,'source_video_and_PCM_unchanged':source_video_hash==sha(silent) and audio_hash==sha(audio)}
    if not args.validate_existing:strict_decode(final)
    result_checks['whole_AV_strict_decode']=True
    report={'revision':10,'status':('PENDING_FINAL_SPEECH' if args.allow_pending_final_speech else 'PASS') if all(result_checks.values()) else 'FAIL','technical_mux_pass':all(result_checks.values()),'final_speech_review_deferred':args.allow_pending_final_speech,'production_complete':False,'final_sha256':sha(final),'final_video_sha256':sha(final),'silent_video_sha256':source_video_hash,'pcm_mix_sha256':audio_hash,'narration_sha256':sha(OUT/'narration.wav'),'timeline_sha256':sha(ROOT/'timeline.json'),'source_identity_sha256':SOURCE_ID,'duration_seconds':315,'frames':9450,'video_stream_sha256':streamhash(final),'audio_encoding':'aac','audio_target_bitrate':256000,'actual_audio_bitrate':encoded.get('bit_rate'),'sample_rate':48000,'channels':2,'speech_tempo':1,'pitch_cents':315,'approved_plan_sha256':PLAN_SHA,'checks':result_checks,'checks_passed':sum(result_checks.values()),'checks_total':len(result_checks),'preflight_receipts':[{'file':name,'sha256':sha(OUT/name),'status':r['status']} for name,r in receipts.items()],'input_bindings':{'timeline.json':sha(ROOT/'timeline.json'),'../out/showcase-v10/video_silent.mp4':source_video_hash,'../out/showcase-v10/audio.wav':audio_hash},'method':'Verified315-second silent video copied without re-encoding; approved final mix encoded once to AAC256k; entire resulting audio/video strictly decoded. Final playback and encoded reviews are separate.'}
    report['validation_mode']='EXISTING_VIDEO_REBOUND_NO_VIDEO_WRITE' if args.validate_existing else 'NEW_MUX_AND_FULL_STRICT_DECODE'
    report['strict_decode_evidence_reused_for_identical_video']=args.validate_existing
    report['input_bindings']['finish.py']=sha(Path(__file__).resolve())
    if args.validate_existing:assert sha(final)==existing['final_sha256']
    save(OUT/'mux-validation.json',report);print(json.dumps({'status':report['status'],'file':str(final),'sha256':report['final_sha256'],'video_rewritten':not args.validate_existing}));assert all(result_checks.values())

if __name__=='__main__':main()
